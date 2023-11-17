# -*- coding: utf-8 -*-
"""
Created on Fri Nov 10 15:47:45 2023

@author: ABarros
"""

import pandas as pd

import matplotlib.pyplot as plt
import folium

import time

start = time.time()

df1= pd.read_excel("14 Nov with Python GPS data with R_cleaned - Duplicates removed.xlsx")

Source= "Traffic"

percentage = round(df1[Source].value_counts(normalize=True)*100,1)
percentage.sort_index()

legend_html = f"""
<style>
@font-face {{
    font-family: 'CustomFont';
    src: url('file:///C:/Users/ABarros/Downloads/MuseoSans_300.otf') format('opentype');
}}
</style>
<div style="position: fixed; bottom: 50px; left: 50px; z-index: 1000; background-color: white; padding: 10px; border: 2px solid grey; font-size: 14px; font-family: 'CustomFont', sans-serif;">
    <b>Presence of traffic</b><br>
    <i style="background: #fedada; border-radius: 50%; width: 15px; height: 15px; display: inline-block;"></i> Helemaal niet: {percentage[1]}% <br>
    <i style="background: #ffa1a1; border-radius: 50%; width: 15px; height: 15px; display: inline-block;"></i> Een beetje: {percentage[2]}%<br>
    <i style="background: #ff3a1e; border-radius: 50%; width: 15px; height: 15px; display: inline-block;"></i> Matig: {percentage[3]}%<br>
    <i style="background: #a70000; border-radius: 50%; width: 15px; height: 15px; display: inline-block;"></i> Veel: {percentage[4]}% <br>
    <i style="background: #2e0000; border-radius: 50%; width: 15px; height: 15px; display: inline-block;"></i> Overheersend: {percentage[5]}%
</div>
"""
m = folium.Map(location=[51.026, 4.476], zoom_start=9) #Mechelen

for i in range(1,len(df1)):

    #"len(df1)"
    latitude,longitude = df1.loc[i-1,"R_GMaps_lat"],df1.loc[i-1,"R_GMaps_lon"]        

    #html = f'<img src="https://raw.githubusercontent.com/Ablenya/Oorzaak/tree/master/Justradarplots/{i}.png">'
    html = f'<img src="https://Ablenya.github.io/Justradarplots/{i}.png">'

    popup = folium.Popup(html,min_width=400, max_width=350,min_height=350, max_height=400)

    rate = df1[Source][i]
  
    if rate == 1:
        colour='#fedada'
    elif rate == 2:
        colour="#ffa1a1"        
    elif rate == 3:
        colour="#ff3a1e"
    elif rate == 4:
        colour="#a70000"        
    elif rate == 5:
        colour="#2e0000"
    folium.Circle(location=[latitude, longitude], popup=popup,radius=20,
                  color=colour,fill=True,fill_color=colour,fill_opacity = 0.7).add_to(m)

m.get_root().html.add_child(folium.Element(legend_html))
m.save(f"Soundof{Source}.html")  

end = time.time()
print(end - start)
#icon="volume-down"