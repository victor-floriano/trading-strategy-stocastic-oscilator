#Stocastic Oscilator

import pandas as pd
import numpy as np
import yfinance as yf
import pandas_datareader as pdr

#The stocastic oscilator is a strategy focused on capturing the change in
#in momentum of a stock. First it creates a range between the maximum and minimum
#price of the stock seen in the past 14 days. The oscilator will be a ratio 
#calculated by the difference between the currently observed price and the last
#minimum price (from the last 14 days), and the spread between the max and min
#prices.

#After the oscilator is calculated, the method also calculates the rolling mean
#of the oscilator values. For this implementation, the size of the rolling mean
#will be defined by the window parameter.The strategy will change its position when
#the current oscilator values crosses its rollingr mean. If the current oscilator
#value at t-1 was lower than the rolling mean and the oscilator value at t 
#becomes larger than the rolling mean, that creates a buy signal (1). On the other
#hand, if the oscilator at t-1 was higher than the rolling mean and the oscilator
#at t is lower than the rolling mean, a sell signal is created (-1). Note that
#the model will only allow for 2 states, it is either fully invested into a stock
#or with no holdings at the stock (after selling its entire position or at the beginning)

#Assumptions: 
#1-To make it more realistic, the model only trades in Open prices. For consistency,
#log returns are also calculated through the difference between Open prices at
#(t) and (t-1)
#2-For this project I'm assuming that the model is able to execute a 
#trade at the exact open price of a stock if needed. 
#3-Additionally, the model currently does not account for dividends or any 
#type of payouts to the stock holders.
#4-The model always executes the trade at the Open price of the stock and also
#calculates the return based of the difference between consective Open prices,
#and not close prices. That may lead to some differences if comparing the returns
#calculated here to historical returns based on close prices.

def calc_stochastic_oscilator(df, column_name='', window = 15): 
    """The inputs are:
    -df: a pandas.DataFrame object that contains one or more columns with the
    numerical data needed to calculate the stocastic oscilator. The data is
    chronologically ordered and the index is a datetime object, representing the dates.
    -column_name: which column of the dataframe contains the required pricing
    data. If no column name is passed in, the function will use the first
    column from left to right.
    -window: how many days will be used to calculate the oscilator's rolling 
    mean, and how many days are used to calculate the max/min observation values
    The function will take those inputs, calculate the daily oscilator value and
    the oscilator rolling mean, and will return a dataframe object with the 
    value of the observation at t, the oscilator value, and its rolling mean value.
    """
    
    #Unless specified, the target column will be the first of the dataframe
    column = df.columns[0]
        
    if column_name != '':
        
        column = column_name
    
    #Creates a new dataframe and adds in the prices in the Observation column,
    #also keeps the index of the original dataframe
    so = pd.DataFrame({'Observation':df[column]}, index = df.index)
    
    #Calculates the maximum priced observed in the last 14 days
    so[f'{window}_day_max'] = so['Observation'].rolling(window).max()
    
    #Calculates the minimum priced observed in the last 14 days
    so[f'{window}_day_min'] = so['Observation'].rolling(window).min()
    
    #Calculates the current oscilator value (as a %)
    so['oscilator'] = ((so['Observation'] - \
                        so[f'{window}_day_min'])/(so[f'{window}_day_max']-\
                                           so[f'{window}_day_min'])) * 100
                                           
    #Calculates the oscilator's rolling mean
    so['oscilator_rolling_mean'] = so['oscilator'].rolling(window).mean()
    
    return so

def create_so_position(so):
    """Takes as an input a pandas.DataFrame object that contains the observed
    prices of a stock, the 14 max/min, the oscilator value and its rolling mean.
    And a 'window' value, which is the window used to calculate the oscilator
    rolling mean in the 'so' DataFrame.
    It then calculates and returns a position_df (DataFrame), that contains the
    strategy result for each period (1=buy all, -1=short all).
    """
    
    #Creates the new position DataFrame
    position_df = pd.DataFrame({'Position':0}, index = so.index)
    
    #Iterates through every period in the input DataFrame
    for i, row in enumerate(so.iterrows()):
        
        #If the oscilator value crosses the roling mean from below it, the 
        #resulting strategy is a buy (1), if it just stays bellow the rolling
        #mean, it maintains the strategy of the last period
        if so['oscilator'].iloc[i-1] < so['oscilator_rolling_mean'].iloc[i-1]:
            
            if so['oscilator'].iloc[i] > so['oscilator_rolling_mean'].iloc[i]:
                position_df.iloc[i] = 1
            else:
                position_df.iloc[i] = position_df.iloc[i-1]
                
                
        #If the oscilator value crosses the roling mean from above, the 
        #resulting strategy is a short (-1), if it just stays bellow the rolling
        #mean, it maintains the strategy of the last period       
        elif so['oscilator'].iloc[i-1] > so['oscilator_rolling_mean'].iloc[i-1]:
            
            if so['oscilator'].iloc[i] < so['oscilator_rolling_mean'].iloc[i]:
                position_df.iloc[i] = 0
            else:
                position_df.iloc[i] = position_df.iloc[i-1]  

    return position_df




def calculate_long_short_returns(df, position, column_name = ''):
    """The parameters are:
    -df, a pandas.DataFrame object with an asset price data series.
    -position, a pandas.DataFrame object with the same index as the parameter
    df, containing a column ‘Position’.
    -column_name, which is the column to use from the DataFrame, containing 
    the asset prices. If not provided, use the first column of from
    theDataFrame.
    And the function calculates and returns a new pandas dataframe with the 
    columns ['Market Return', 'Strategy Return', and 'Abnormal Return']
    """
    
    #If not column name is passed in, the price column to be used will be the
    #first column of the dataset
    column = df.columns[0]
    
    #If a column is specified, the column to be used changes to the specified 
    #column
    if column_name != '':
        
        column = column_name
    
    #Creates a new DataFrame that will contain the market returns
    returns_df = pd.DataFrame({'Log Market Return':0}, index = df.index)
    
    #Calculates the log returns of the asset 
    returns_df['Log Market Return'] = np.log(df[column]) - np.log(df[column].shift(1))
    
    #Calculates the log strategy return. Observe that when calculating the strategy
    #return, we need to take into account the position held at the previous day. For
    #example, if the market opens today and the open price today means a return of 
    #2% was achieved from the open price yesterday, the strategy only accumulates 
    #such return if the position was 1 yesterday.
    returns_df['Log Strategy Return'] = position['Position'].shift(1) *\
        returns_df['Log Market Return']
        
    #Calculates the log abnormal return, the difference between the strategy and the
    #market return
    returns_df['Log Abnormal Return'] = returns_df['Log Strategy Return']\
        - returns_df['Log Market Return']
    
    
    return returns_df


 

def plot_cumulative_returns(df, asset=''):
    """Create a plot of the cumulative return for each column in the parameter
    df, a pandas.DataFrame object with one or more series of returns.
    """
    
    df.cumsum().plot(xlabel='Date', title=f'Cumulative Returns {asset}')





if __name__ == '__main__':
    
    df = yf.download('BBAS3.SA','2022-01-01','2022-12-31')

    df = df.sort_values(by='Date', axis=0, ascending=True)[['Open']]
    
    so = calc_stochastic_oscilator(df, column_name='Open', window = 14)
    
    position = create_so_position(so)
    
    returns = calculate_long_short_returns(df, position, column_name = 'Open')

    plot_cumulative_returns(returns, asset='BBAS3') 

 
    
    
    
    
    
    
    