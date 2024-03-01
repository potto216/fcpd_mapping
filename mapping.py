import folium
from folium import plugins
import geopandas as gpd
import numpy as np
import pandas as pd
import streamlit as st

import cache

def Choropleth(m, geojson_link, df, bounds_on, df_on, data_label, tooltip_labels, 
               test=None, skip_test=True, max_val=None, exclude=[], opacity=0.6, legend=True):
    bounds = cache.load_geojson(geojson_link)
    
    if len(exclude)>0:
        bounds = bounds[~bounds[bounds_on].isin(exclude)]

    if not skip_test:
        districts = bounds[bounds_on].unique()
        districts_arrests = df[df_on].unique()

        for d in districts_arrests:
            if d not in ['UNVERIFIED',-1, 0] and d not in districts and (not test or test(d)):
                raise ValueError(f"Unknown value: {d}")
        
    
    vc = df[df_on].astype(str).value_counts()
    vc.name = data_label

    bounds = bounds.drop_duplicates(subset=bounds_on)
    bounds[bounds_on] = bounds[bounds_on].astype(str)

    bounds = bounds.merge(vc, how='left', left_on=bounds_on, right_on=df_on)

    geo = gpd.GeoSeries(bounds.set_index(bounds_on)['geometry']).to_json()

    num_bins = 10
    if not max_val:
        max_val = bounds[data_label].max()
        bins = np.linspace(0, max_val, num_bins)
    else:
        bins = np.append(np.linspace(0, max_val, num_bins-1), bounds[data_label].max())


    # https://towardsdatascience.com/how-to-step-up-your-folium-choropleth-map-skills-17cf6de7c6fe
    cp = folium.Choropleth(
        geo_data=geo,
        data=bounds,
        columns=[bounds_on, data_label],
        key_on = 'feature.id',
        legend_name = '# of Arrests',
        nan_fill_color='White',
        highlight=True,
        bins=bins,
        name="Data Plot",
        fill_opacity=opacity,
    ).add_to(m)

    if not legend:
        for key in cp._children:
            if key.startswith('color_map'):
                del(cp._children[key])

    for row in cp.geojson.data['features']:
        row['properties'][bounds_on] = row['id']
        if (tf:=bounds[bounds_on].apply(str)==row['id']).any():
            val = bounds[data_label][tf].iloc[0]
            if pd.notnull(val):
                row['properties'][data_label] = str(int(val))
            else:
                row['properties'][data_label] = '0'
        else:
            row['properties'][data_label] = '0'
        
    folium.GeoJsonTooltip([bounds_on,data_label],aliases=tooltip_labels).add_to(cp.geojson)


def add_overlays(map_type, county_bounds, df_rem, m, geo_data, opacity, legend=True):
    if map_type=='Individual Locations':
        geo_j = gpd.GeoSeries(county_bounds.iloc[0]['geometry']).to_json()
        geo_j = folium.GeoJson(data=geo_j, style_function=lambda x: {"fillOpacity": 0.0}, name='County Boundary')

        points = [[point.xy[1][0], point.xy[0][0]] for point in df_rem.geometry]
        plugins.HeatMap(points, radius = 4, blur = 1, name="Data Plot").add_to(m)
        geo_j.add_to(m)
    else:
        Choropleth(m, geo_data[map_type]['geojson'], df_rem, geo_data[map_type]['bounds_on'], geo_data[map_type]['df_on'], 
                'ARRESTS', [f'{map_type}:','# of Arrests: '], opacity=opacity, legend=legend)


def add_markers(m):
    df_markers = st.session_state['markers'].replace('',pd.NA).dropna(subset=['Latitude','Longitude'])
    for k in st.session_state['marker_groups'].index:
        members = df_markers['Group']==st.session_state['marker_groups'].loc[k, 'Name']
        if members.any():
            fg=folium.FeatureGroup(name=st.session_state['marker_groups'].loc[k, 'Name'], show=True)
            m.add_child(fg)
            for j in members[members].index:
                color = st.session_state['marker_groups'].loc[k, 'Color'] if (c:=df_markers.loc[j, 'Color'])=='Group Color' else c
                name = df_markers.loc[j, 'Name'] if pd.notnull(df_markers.loc[j, 'Name']) else None
                folium.Marker([df_markers.loc[j, 'Latitude'], df_markers.loc[j, 'Longitude']], 
                                tooltip=name,
                                popup=name,
                                icon=folium.Icon(color=color, icon=None)
                                ).add_to(fg)