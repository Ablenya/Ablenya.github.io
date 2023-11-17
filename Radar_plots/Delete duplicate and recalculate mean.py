# -*- coding: utf-8 -*-
"""
Created on Tue Oct 31 08:28:07 2023

@author: ABarros
"""

import pandas as pd
import numpy as np

df1= pd.read_excel("17 Nov with R GPS data_cleaned.xlsx")
  
"""    
dict = {"Traffic":"Verkeer","Human sounds":"Menselijk geluid","Music":"Muziek",
        "Natural sounds":"Natuurgeluiden","Industry":"Industrie","Construction":"Bouwwerken en/of onderhoudswerken",
        "Alarms / priority vehicles":"Alarmsignalen / prioritaire voertuigen", "Silence":"Stilte",
        "Rate_soundscape":"Hoe aangenaam","Favourite":"Favoriete geluid","Least":"Minst aangenaam",
        }
df1.rename(columns=dict,inplace=True)


for i in ["Verkeer","Menselijk geluid","Muziek","Natuurgeluiden","Industrie",
          "Bouwwerken en/of onderhoudswerken","Alarmsignalen / prioritaire voertuigen",
          "Stilte","Hoe aangenaam"]:
    df1[i] =df1.groupby(['R_GMaps_lat', 'R_GMaps_lon'])[i].transform('mean')
    df1[i]=round(df1[i]) 
"""
for i in ["Traffic","Human sounds","Music","Natural sounds","Industry",
          "Construction","Alarms / priority vehicles",
          "Silence","Rate_soundscape"]:
    df1[i] =df1.groupby(['R_GMaps_lat', 'R_GMaps_lon'])[i].transform('mean')
    df1[i]=round(df1[i]) 

# Drop duplicate rows based on "Real latitude" and "Real longitude," keeping the first occurrence
df1.drop_duplicates(subset=['R_GMaps_lat', 'R_GMaps_lon'], keep='first', inplace=True)

# Reset the index
df1.reset_index(drop=True, inplace=True)

counts=df1['Repeated_R'].value_counts()
df1=df1.drop('index', axis =1)
df1.to_excel('17 Nov with R GPS data_cleaned - Duplicates removed.xlsx', index=False)
