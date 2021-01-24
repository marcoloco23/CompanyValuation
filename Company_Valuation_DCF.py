# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st
import seaborn as sns
import requests
from bs4 import BeautifulSoup as bs
from urllib.request import urlopen
import json
import sys


# %%

def get_jsonparsed_data(url):
    response = urlopen(url)
    data = response.read().decode("utf-8")
    return json.loads(data)


# %%
def get_stocks():
    table=pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
    df = table[0].iloc[:,0]
    stocks = np.array(sorted(df.tolist()))
    for m in stocks:
        if '.' in m:
            stocks = stocks[stocks != m]
            
    return stocks


# %%
def get_q_cash_flow_statement(base_url,ticker,apiKey):
    q_cash_flow_statement = pd.DataFrame({'A' : []})

    try:
        q_cash_flow_statement = pd.DataFrame(get_jsonparsed_data(base_url+'cash-flow-statement/'+ticker+'?period=quarter'+'&apikey='+apiKey))
    except ValueError:
        sys.exit(get_jsonparsed_data(base_url+'cash-flow-statement/'+ticker+'?period=quarter'+'&apikey='+apiKey)) 

    q_cash_flow_statement = q_cash_flow_statement.set_index('date').iloc[:4]
    q_cash_flow_statement = q_cash_flow_statement.apply(pd.to_numeric, errors='coerce')

    return q_cash_flow_statement


# %%
def get_cash_flow_statement(base_url,ticker,apiKey):
    cash_flow_statement = pd.DataFrame(get_jsonparsed_data(base_url+'cash-flow-statement/'+ticker+'?apikey='+apiKey))
    cash_flow_statement = cash_flow_statement.set_index('date')
    cash_flow_statement = cash_flow_statement.apply(pd.to_numeric, errors='coerce')

    return cash_flow_statement


# %%
def get_final_cash_flow_statement(base_url,ticker,apiKey):
    ttm_cash_flow_statement = get_q_cash_flow_statement(base_url,ticker,apiKey).sum()
    cash_flow_statement = get_cash_flow_statement(base_url,ticker,apiKey)[::-1].append(ttm_cash_flow_statement.rename('TTM')).drop(['netIncome'],axis=1)
    final_cash_flow_statement = cash_flow_statement[::-1]
    
    return final_cash_flow_statement


# %%
def get_q_balance_statement(base_url,ticker,apiKey):
    q_balance_statement = pd.DataFrame(get_jsonparsed_data(base_url+'balance-sheet-statement/' + ticker + '?period=quarter' + '&apikey=' + apiKey))
    q_balance_statement = q_balance_statement.set_index('date')
    q_balance_statement = q_balance_statement.apply(pd.to_numeric, errors='coerce')

    return q_balance_statement


# %%
def fundamental_metric(soup, metric):
    # the table which stores the data in Finviz has html table attribute class of 'snapshot-td2'
    return soup.find(text = metric).find_next(class_='snapshot-td2').text
   
def get_finviz_data(ticker):
    try:
        url = ("http://finviz.com/quote.ashx?t=" + ticker.lower())
        soup = bs(requests.get(url,headers={'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:20.0) Gecko/20100101 Firefox/20.0'}).content)
        dict_finviz = {}        
        for m in metric:   
            dict_finviz[m] = fundamental_metric(soup,m)
        for key, value in dict_finviz.items():
            # replace percentages
            if (value[-1]=='%'):
                dict_finviz[key] = value[:-1]
                dict_finviz[key] = float(dict_finviz[key])
            # billion
            if (value[-1]=='B'):
                dict_finviz[key] = value[:-1]
                dict_finviz[key] = float(dict_finviz[key])*1000000000  
            # million
            if (value[-1]=='M'):
                dict_finviz[key] = value[:-1]
                dict_finviz[key] = float(dict_finviz[key])*1000000
            try:
                dict_finviz[key] = float(dict_finviz[key])
            except:
                pass 
    except Exception as e:
        print (e)
        print ('Not successful parsing ' + ticker + ' data.')        
    return dict_finviz


# %%
def get_discount_rate(Beta):
    discount_rate = 7
    if(Beta<0.80):
        discount_rate = 5
    elif(Beta>=0.80 and Beta<1):
        discount_rate = 6
    elif(Beta>=1 and Beta<1.1):
        discount_rate = 6.5
    elif(Beta>=1.1 and Beta<1.2):
        discount_rate = 7
    elif(Beta>=1.2 and Beta<1.3):
        discount_rate =7.5
    elif(Beta>=1.3 and Beta<1.4):
        discount_rate = 8
    elif(Beta>=1.4 and Beta<1.6):
        discount_rate = 8.5
    elif(Beta>=1.61):
        discount_rate = 9
    
    return discount_rate


# %%
def st_write(cash_flow,total_debt,cash_and_ST_investments,EPS_growth_5Y,EPS_growth_6Y_to_10Y,EPS_growth_11Y_to_20Y,PE,Beta,discount_rate,shares_outstanding):
    st.write("Free Cash Flow: ", cash_flow)
    st.write("Total Debt: ", total_debt)
    st.write("Cash and ST Investments: ", cash_and_ST_investments)
    st.write("EPS Growth 5Y: ", EPS_growth_5Y)
    st.write("EPS Growth 6Y to 10Y: ", EPS_growth_6Y_to_10Y)
    st.write("EPS Growth 11Y to 20Y: ", EPS_growth_11Y_to_20Y)
    st.write("P/E: ", PE)
    st.write("Beta: ", Beta)
    st.write("Discount Rate: ", discount_rate)
    st.write("Shares Outstanding: ", shares_outstanding)


# %%
def calculate_intrinsic_value(cash_flow, total_debt, cash_and_ST_investments, 
                                  EPS_growth_5Y, EPS_growth_6Y_to_10Y, EPS_growth_11Y_to_20Y,
                                  shares_outstanding, discount_rate):   
    
    # Convert all percentages to decmials
    EPS_growth_5Y_d = EPS_growth_5Y/100
    EPS_growth_6Y_to_10Y_d = EPS_growth_6Y_to_10Y/100
    EPS_growth_11Y_to_20Y_d = EPS_growth_11Y_to_20Y/100
    discount_rate_d = discount_rate/100
    
    # Lists of projected cash flows from year 1 to year 20
    cash_flow_list = []
    cash_flow_discounted_list = []
    year_list = []
    
    
    # Years 1 to 5
    for year in range(1, 6):
        year_list.append(year)
        cash_flow*=(1 + EPS_growth_5Y_d)        
        cash_flow_list.append(cash_flow)
        cash_flow_discounted = cash_flow/((1 + discount_rate_d)**year)
        cash_flow_discounted_list.append(cash_flow_discounted)
        
    
    # Years 6 to 10
    for year in range(6, 11):
        year_list.append(year)
        cash_flow*=(1 + EPS_growth_6Y_to_10Y_d)
        cash_flow_list.append(cash_flow)
        cash_flow_discounted = cash_flow/((1 + discount_rate_d)**year)
        cash_flow_discounted_list.append(cash_flow_discounted)
        
    
    # Years 11 to 20
    for year in range(11, 21):
        year_list.append(year)
        cash_flow*=(1 + EPS_growth_11Y_to_20Y_d)
        cash_flow_list.append(cash_flow)
        cash_flow_discounted = cash_flow/((1 + discount_rate_d)**year)
        cash_flow_discounted_list.append(cash_flow_discounted)
        
    intrinsic_value = (sum(cash_flow_discounted_list) - total_debt + cash_and_ST_investments)/shares_outstanding

    return intrinsic_value


# %%
def st_write_2(intrinsic_value,current_price):
    st.write("Intrinsic Value: ", intrinsic_value)
    st.write("Current Price: ", current_price)
    st.write("Margin of Safety: ", (1-current_price/intrinsic_value)*100)


# %%
def main():
    base_url = "https://financialmodelingprep.com/api/v3/"
    apiKey = "89f5d1f558c5ccf28999c7529f14af21"
    ticker = st.selectbox('Stock Ticker?', get_stocks())
    final_cash_flow_statement = get_final_cash_flow_statement(base_url,ticker,apiKey)
    st.bar_chart(final_cash_flow_statement[['freeCashFlow']].iloc[::-1].iloc[-15:])
    cash_flow = final_cash_flow_statement.iloc[0]['freeCashFlow']
    q_balance_statement = get_q_balance_statement(base_url,ticker,apiKey)
    total_debt = q_balance_statement.iloc[0]['totalDebt'] 
    cash_and_ST_investments = q_balance_statement.iloc[0]['cashAndShortTermInvestments']
    metric = ['Price', 'EPS next 5Y', 'Beta', 'Shs Outstand','P/E']
    finviz_data = get_finviz_data(ticker)
    EPS_growth_5Y = finviz_data['EPS next 5Y']
    EPS_growth_6Y_to_10Y = EPS_growth_5Y/2
    EPS_growth_11Y_to_20Y  = np.minimum(EPS_growth_6Y_to_10Y, 4)
    PE = finviz_data['P/E']
    shares_outstanding = finviz_data['Shs Outstand']
    st_write(cash_flow,total_debt,cash_and_ST_investments,EPS_growth_5Y,EPS_growth_6Y_to_10Y,EPS_growth_11Y_to_20Y,PE,Beta,discount_rate,shares_outstanding)
    intrinsic_value = calculate_intrinsic_value(cash_flow, total_debt, cash_and_ST_investments, 
                                  EPS_growth_5Y, EPS_growth_6Y_to_10Y, EPS_growth_11Y_to_20Y,
                                  shares_outstanding, discount_rate)
    st_write_2(intrinsic_value,current_price)


# %%
if __name__ == '__main__':
    main()


