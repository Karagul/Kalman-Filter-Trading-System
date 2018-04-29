
"""Main script for running the trading system, calls all other programs.

This code will be the main script called for running the trading system. As of
now, weekends and holidays must be specified separately in order to run the 
system for more than a couple of days. 

The system will in the beginning run a "burn-in" for the Kalamn filter the 
length of which canc be specified. Now at first this and the weekends will
be set inside the code. 

The program calls the datetime.now().second every one second and for keeping
time, and calls the Kalman filter to do its calculations at the beginning of 
each hour. If the Kalman filter returns a buy or sell signal, depending on if 
there are any open trades, the program will call the appropriate modules for 
dealing with the opening or closing requests. 


"""
# Import standard python stuff 
import numpy as np
import time
import datetime

# Import oandapyV20 stuff
import oandapyV20
import oandapyV20.endpoints.instruments as instruments
from oandapyV20.contrib.requests import MarketOrderRequest
import oandapyV20.endpoints.orders as orders
import oandapyV20.endpoints.trades as trades
import oandapyV20.endpoints.accounts as accounts
from oandapyV20.exceptions import V20Error

# Import my own stuff
from oKalman import KalmanCoint
import oTradingOperations as to


# First specify account ID and number
Account_ID = '...'
Account_Token = '...'


# Specify the burn-in as well as the dates for all Fridays. The program will
# sleep from Friday 5pm to Sunday 5pm. All times are EST!!

burn_in = .... # The last hour is presumably the current hour not to be used
fridays = [(..,..),(..,..),...] # Put the Fridays in a (day,month) tuple 


# Set up the Kalman filter, for now using the standard values for our
# 5 currency pair strategy.

print '\n Initializing the Kalman filter. \n'

# These need to be specified properly for real use
x_0 = np.array([[1],[1],[1],[1],[1]])
P_0 = np.ones((5,5))
A = np.eye(5)
Q = np.eye(5) 
R = 1
kf = KalmanCoint(x_0, P_0, A, Q, R) # Initialize Kalman filter

# Initialize the position manager
Instruments = ['EUR_USD', 'GBP_USD', 'AUD_USD', 'USD_CAD', 'USD_JPY']
I_types = [1,1,1,2,2] # How the lots are calculated
positions = to.oPositionManager(Account_ID, Account_Token, Instruments, I_types)


print '\n Doing the burnin with', burn_in-1, 'candles.\n'


# Get the data for the burnin, calls oGetData()
z_m, H_m = positions.oGetData(burn_in) 

# Define an array for calculating the rolling mean and std
Z = np.empty(len(z_m)) 

# Do the burn-in
for i in xrange(len(z_m)):
    kf.Filtering(z_m[i], H_m[i:i+1,:]) # Numpys funny slicing conventions...
    Z[i] = z_m[i]-np.dot(H_m[i:i+1], kf.x_pri)
Z = Z[1:]

print '\n Current state values:'
print 'Basket:         ', Z[-1]
print 'Basket mean:    ', np.mean(Z)
print 'Basket STD:     ', np.std(Z, ddof=1)
print 'State prior:    ', kf.x_pri
print 'State posterior:', kf.x_pos, '\n'


# Get the current hour of the day and print the current time and date
dt = datetime.datetime.now()
current_hour = dt.hour

print '\n Starting up time and date: ', dt.strftime('%H:%M:%S %d.%m.%Y'), '\n'

# -------------------- Start the system --------------------------------------

print '\n System initialized, terminate wiht Ctrl-c \n'
try:
    while True:

        # Get the date and time
        dt = datetime.datetime.now()

        # If we are in the active trading period of the week up until last hour:
        if ((dt.day,dt.month) not in fridays) or (dt.hour<=16):

            # If new hour
            if dt.hour!=current_hour:

                print '\n New hour: ', dt.strftime('%H:%M:%S %d.%m.%Y')
                print 'Filtering & trading...:\n'

                # Do possible trading
                # Get the last prices
                z, H, Trade, ERR = positions.oLastPrice()
                if ERR==False:
                    kf.Filtering(z, H)

                    # Current values of the cointegrated portfolio
                    Z = np.append(Z,float(z-np.dot(H, kf.x_pri)))
                    Z = Z[1:]
                    print 'LEN:', len(Z)
                    Z_mean = np.mean(Z)
                    Z_std = np.std(Z,ddof=1)

                    print ' Current basket values:'
                    print 'Basket: ', Z[-1]
                    print 'Mean:   ', Z_mean
                    print 'STD:    ', Z_std
    
                    print '\n Current state values:'
                    print 'State prior:    ', kf.x_pri
                    print 'State posterior:', kf.x_pos, '\n'

                    # Manage positions 
                    if Trade==False:
                        print '\n Due to error in getting prices on time,'
                        print 'not opening or closing new positions.\n'
                    elif Trade==True:
                        positions.oManage(kf.x_pri[0:-1], H, Z[-1],
                                          Z_mean, Z_std)

                    else:
                        print '\nERROR IN GETTING DATA FOR THE PREVIOUS HOUR!\n'

                current_hour = dt.hour # Update the hour counter

            # If not new hour, wait a second and try again.
            else: time.sleep(1)

        # If trading has just closed, wait until Sunday
        else:

            print '\n Trading Closed!!', dt.strftime('%H:%M:%S %d.%m.%Y')
            time.sleep(172800)
            dt = datetime.datetime.now() 
            print '\n Trading Opened!!', dt.strftime('%H:%M:%S %d.%m.%Y'), '\n'
            current_hour = 0

except KeyboardInterrupt:

    dt = datetime.datetime.now()
    print '\n Program terminated at', dt.strftime('%H:%M:%S %d.%m.%Y'), '\n'

   
        

                  


