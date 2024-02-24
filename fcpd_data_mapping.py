import datetime
import folium
from folium import plugins
from geopy.geocoders import Nominatim
import openpolicedata as opd
import pandas as pd
import pyproj
import streamlit as st
from streamlit_utils import data_editor_on_change
from streamlit_folium import folium_static

import cache
import config
from mapping import add_overlays

# TODO: Markers: KML, Geocode

st.set_page_config(layout='wide')

group_color = 'Group Color'
marker_colors = ['red', 'blue', 'green', 'purple', 'orange', 'darkred', 'lightred', 
                 'beige', 'darkblue', 'darkgreen', 'cadetblue', 'darkpurple', 'white', 
                 'pink', 'lightblue', 'lightgreen', 'gray', 'black', 'lightgray']
marker_colors_w_group = [group_color]
marker_colors_w_group.extend(marker_colors)

default_color = 'blue'
default_group = 'Default Group'
if 'markers' not in st.session_state:
    st.session_state['markers'] = pd.DataFrame(columns=['Name','Latitude','Longitude','Group','Color'])
    # st.session_state['markers_saved'] = st.session_state['markers'].copy()

    d = {'Name': [default_group], 
         'Color':[default_color],
    }
    st.session_state['marker_groups'] = pd.DataFrame(d)
    # st.session_state['marker_groups_saved'] = st.session_state['marker_groups'].copy()
    st.session_state['unfreeze_disable'] = True
    st.session_state['frozen_filters'] = None

county_bounds = cache.get_county_bounds()
bounds = county_bounds.total_bounds
lon_center = (bounds[0] + bounds[2]) / 2
lat_center = (bounds[1] + bounds[3]) / 2

with st.sidebar:
    table_type = st.selectbox("Data Type", ['ARRESTS'], help='Currently, only arrests 2022 data is available. More data will be available in the future '+
                              'Please notify if there is an immediate need for more data')
    
    year = st.selectbox("Data Year", [2022], help='Currently, only arrests 2022 data is available. More data will be available in the future '+
                              'Please notify if there is an immediate need for more data')
    
    map_type = st.selectbox('Geographic Unit (Most General to Most Specific)',
                            config.geo_data.keys(),
                            index=[k for k,x in enumerate(config.geo_data.keys()) if x=='Patrol Area'][0])
    
    df = cache.get_data(table_type, year)

    options = cache.get_statute_options(df)
    default = [x for x in options if x.startswith('5/1/2001: DRUNK IN PUBLIC OR PROFANE')]
    statutes = st.multiselect("Statutes", options, default=default, 
                   help='Type in this box to search for statutes')
    
    statutes_list = [x[:x.rfind(" (")] for x in statutes]

    df_rem = df[df['Statute Full'].isin(statutes_list)]

    races = st.multiselect("Race/Ethnicity", df_rem[opd.defs.columns.RE_GROUP_SUBJECT].unique(),
                           default=df_rem[opd.defs.columns.RE_GROUP_SUBJECT].unique(),
                           help='More demographics filters (gender, age) can be added')
    
    df_rem = df_rem[df_rem[opd.defs.columns.RE_GROUP_SUBJECT].isin(races)]

    st.text(f"Total Selected: {len(df_rem)}")

st.info("Hover over question marks and buttons for helpful hints on using this dashboard. Add markers and adjust settings below map.")

st.header(f"Heat Map of Arrests" if map_type=='Individual Locations' else f"Number of Arrests in Each {map_type}")
col1, col2, col3 = st.columns(3)
with col1:
    def freeze_click():
        st.session_state['unfreeze_disable'] = False
        st.session_state['frozen_filters'] = {'map_type': map_type, 
                                            'statutes': statutes, 
                                            'races': races,
                                            'df_rem': df_rem.copy()}
    st.button('Freeze', on_click=freeze_click, help="Click this button to keep the current map and compare to a 2nd map.")

plot_dual = st.session_state['frozen_filters']!=None
if plot_dual:
    with col2:
        def unfreeze_click():
            st.session_state['unfreeze_disable'] = True
            st.session_state['frozen_filters'] = None
        st.button('Unfreeze', disabled=st.session_state['unfreeze_disable'], on_click=unfreeze_click,
                help="Click this button to return to a single map.")
        
with col3:
    download_container = st.container()

map = plugins.DualMap if plot_dual else folium.Map

zoom_start = 10 if plot_dual else 10
map_container = map(location=[lat_center, lon_center], zoom_start=zoom_start, min_zoom=zoom_start)

m = map_container.m2 if plot_dual else map_container

container = st.container(border=False)

opacity = st.slider('Opacity', 0.0, 1.0, 0.6, step=0.05) if map_type!='Individual Locations' else None
add_overlays(map_type, county_bounds, df_rem, m, config.geo_data, opacity, legend=not plot_dual)
if plot_dual:
    opacity = st.slider('Opacity', 0.0, 1.0, 0.6, step=0.05) \
        if st.session_state['frozen_filters']['map_type']!='Individual Locations' and not opacity else opacity
    add_overlays(st.session_state['frozen_filters']['map_type'], county_bounds, 
                 st.session_state['frozen_filters']['df_rem'], map_container.m1, config.geo_data, opacity, legend=False)

with container:
    if plot_dual:
        col1, col2 = st.columns(2)
        with col1:
            st.info("Left map is filtered for: \n\n"+
                    f"**Statutes**: {', '.join(st.session_state['frozen_filters']['statutes'])}\n\n"+
                    f"**Races**: {', '.join(st.session_state['frozen_filters']['races'])}\n\n")
        with col2:
            st.info("Left map is filtered for the current filter selections")
    width = 1000 if plot_dual else 700
    folium_static(map_container, width=width)#, use_container_width=True)

download_container.download_button(
    label='Download Map',
    data = cache.map_to_html(str(plot_dual), map_type, statutes, races, map_container),
    file_name="map_"+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'+".html"),
    help="Download current map as HTML file"
)

marker_config = {
    'Latitude' : st.column_config.NumberColumn(format="%.5f"),
    'Longitude' : st.column_config.NumberColumn(format="%.5f"),
    'Group': st.column_config.SelectboxColumn(default='Default Group', 
                                              options=st.session_state['marker_groups']['Name'].replace("",pd.NA).dropna(), required=True),
    'Color': st.column_config.SelectboxColumn(default=group_color, options=marker_colors, required=True)
}
group_config = {
    'Color': st.column_config.SelectboxColumn(default=default_color, options=marker_colors, required=True)
}

with st.expander("Add Markers to Map", expanded=True):
    default_address = 'Type address to find Lat/Long for new marker and click Enter'
    def address_on_change():
        st.session_state['address_entered'] = True
        if len(st.session_state.address.strip())>0 and st.session_state.address!=default_address:
            geolocator = Nominatim(user_agent="FCPD Mapping Dashboard")
            try:
                location = geolocator.geocode(st.session_state.address)
                # Check that found location is suitably close
                transformer = pyproj.Transformer.from_crs("EPSG:4326", config.crs)
                x0,y0 = transformer.transform(lat_center, lon_center)
                x1,y1 = transformer.transform(location.latitude, location.longitude)
                units = pyproj.CRS.from_epsg(2283).coordinate_system.axis_list[0].unit_name

                if units!='US survey foot':
                    raise ValueError("Currently, only units of feet can be tested. Notify dashboard ")
                
                dist = ((x1-x0)**2 + (y1-y0)**2)**0.5 / 5280
                if dist>100:
                    # This is really far away and unlikely to have been user's desired marker location
                    st.toast(f"Latitude/Longitude found is {round(dist)} miles from center of map and is unlikely to be desired location. "+
                             "Marker not added.")
                    
                st.session_state['markers'] = pd.concat([st.session_state['markers'], 
                                pd.DataFrame([('',location.latitude, location.longitude,default_group,group_color)], 
                                             columns=st.session_state['markers'].columns)],
                                ignore_index=True)
            except:
                st.toast(f"Latitude/Longitude not found for {st.session_state.address}")

    st.text_input(label='Address for New Marker',
                  key='address',
                  placeholder=default_address,
                  on_change=address_on_change,
                  help="Type address and click Enter to find Latitude and Longitude for a location. "+
                        "Latitude/Longitude will be added to Markers table and displayed on map.")

    st.subheader("Markers",
                 help="List of markers. To delete a marker, click on the empty column on the left and then click the track can icon "+
                    "above the table on the right.")
    st.data_editor(st.session_state['markers'], 
                    num_rows='dynamic',  
                    key='df_markers',
                    on_change=lambda: data_editor_on_change('df_markers', 'markers'),
                    column_config=marker_config,
                    hide_index=True)

    st.subheader("Marker Groups",
                  help="Marker groups allow multiple markers to be in the same layer in the map so they can can be hidden "+
                        "and unhidden together in the layer controls (white box with the stacked squares in the upper right of the map). "+
                        "To delete a group, click on the empty column on the left and then click the track can icon "+
                        "above the table on the right.")
    st.data_editor(st.session_state['marker_groups'], 
                    key='df_marker_groups',
                    on_change=lambda: data_editor_on_change('df_marker_groups', 'marker_groups'),
                    num_rows='dynamic', 
                    column_config=group_config,
                    hide_index=True)


st.divider()
st.markdown("The dashboard is generated using data from the "+
            "[Fairfax County Police Open Data Portal](https://www.fcpod.org/pages/crime-data). "+
            "[OpenPoliceData](https://openpolicedata.readthedocs.io/) was used to load data into this dashboard " +
            "and is freely available for others to easily download the raw data.\n\n"+
            'Report issues, feature requests, or suggestions to openpolicedata@gmail.com or our [GitHub issues page](https://github.com/sowdm/fcpd_mapping/issues).')