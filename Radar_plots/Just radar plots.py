# -*- coding: utf-8 -*-
"""
Created on Tue Oct 31 07:55:44 2023

@author: ABarros
"""

import soundscapy as sspy
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import time
from matplotlib.font_manager import FontProperties
import time

start = time.time()

df1= pd.read_excel("17 Nov with R GPS data_cleaned.xlsx")


#dataframe with only attributes 
df_attributes = df1[["pleasant","vibrant","eventful","chaotic",
                      "annoying","monotonous","uneventful","calm"]]

#creates map
angles = [0,45,90,135,180,225,270,315]
labels=['     Prettig','       Levendig','Dynamisch','Chaotisch        ','Vervelend          ','Eentonig         ','Statisch','          Rustgevend']

plt.rcParams["figure.dpi"] = 85
plt.ioff()
#plt.show()

df1["Done"] = np.nan
df1['ID']=np.nan
n=1
for i in range(len(df1)):
    #"len(df1)"
    if df1.loc[i,"Done"] == 1: 
        continue
    latitude,longitude = df1.loc[i,"R_GMaps_lat"],df1.loc[i,"R_GMaps_lon"]
    fig = plt.figure(figsize=(4.92, 4.5))

    rate=np.nan
    custom_font = FontProperties(fname="C:/Users/ABarros/Downloads/MuseoSans_300.otf", size=12)    

    #in case of repeated GPS location, add all the 3 first webs in the same plot
    if ~(np.isnan(df1.loc[i,"Repeated_R"])):
        subset_repeated = df1[df1["Repeated_R"] == df1.loc[i,"Repeated_R"]]

        attributes_repeated = subset_repeated[["pleasant","vibrant","eventful","chaotic",
                              "annoying","monotonous","uneventful","calm"]]
        df1.loc[df1["Repeated_R"] == df1.loc[i,"Repeated_R"], "Done"] = 1

        ax = sspy.plotting.likert.paq_radar_plot(attributes_repeated[0:3]);
        legend_label = subset_repeated['DateandTime_Brussels']
        handles, previous_labels = ax.get_legend_handles_labels()
        ax.legend(handles=handles, labels=legend_label.values.tolist(),
                  loc='best',bbox_to_anchor=(0.42, 0.08),
                  prop=FontProperties(fname="C:/Users/ABarros/Downloads/MuseoSans_300.otf", size=11))
      
    else:
        ax = sspy.plotting.likert.paq_radar_plot(df_attributes.iloc[[i],:]);
        legend_label = df1.loc[i,'DateandTime_Brussels']
        ax.legend([legend_label],loc='best',bbox_to_anchor=(0.42, 0),
                  prop=FontProperties(fname="C:/Users/ABarros/Downloads/MuseoSans_300.otf", size=11))
    
    ax.set_thetagrids(angles=angles, labels=labels,  fontproperties=custom_font)  
    ax.set_rlabel_position(-90)
    ax.xaxis.set_tick_params(pad=5)
    custom_font = FontProperties(fname="C:/Users/ABarros/Downloads/MuseoSans_900.otf", size=14)    

    ax.set_title("Jouw geluidslandschap", fontproperties=custom_font)

    fig = ax.get_figure()
    
    df1.loc[i,'ID']=n
    n=n+1
    fig.savefig(f"{int(df1.loc[i,'ID'])}.png", format='png')

end = time.time()
print(end - start)
#icon="volume-down"