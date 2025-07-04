# -*- coding: utf-8 -*-


# !pip install earthengine-api geemap streamlit plotly pandas geopandas folium numpy

# # Install the Google Cloud SDK
# !echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
# !curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -
# !sudo apt-get update
# !sudo apt-get install google-cloud-sdk -y

# # Install Earth Engine Python API
# !pip install earthengine-api --upgrade

# run this first
import ee
import geemap
from google.colab import auth
import subprocess
from google.colab import files

def authenticate_gee_with_project():
    # 1. Authenticate with Google Cloud
    auth.authenticate_user()

    # 2. Create credentials
    from oauth2client.client import GoogleCredentials
    credentials = GoogleCredentials.get_application_default()

    # 3. Get project ID
    # You'll need to run this in a separate cell to get your project ID
    !gcloud config list project

    # 4. Initialize Earth Engine with project
    # Replace YOUR_PROJECT_ID with the project ID from step 3
    ee.Initialize(project='landsat-colab')

    print("Successfully authenticated with Google Earth Engine!")

# First, install necessary packages
!pip install google-cloud-sdk
!apt-get install google-cloud-sdk

# Run authentication
try:
    authenticate_gee_with_project()
except Exception as e:
    print(f"Authentication failed: {str(e)}")

# import ee
# from google.colab import auth
# import subprocess

# # First, install the necessary packages correctly
# !curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -
# !echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
# !sudo apt-get update
# !sudo apt-get install google-cloud-sdk -y

# def authenticate_and_initialize():
#     # Authenticate
#     auth.authenticate_user()

#     # Create a new project if none exists
#     project_name = 'landsat-colab'  # You can change this name
#     try:
#         !gcloud projects create {project_name}
#     except:
#         print(f"Project {project_name} may already exist, continuing...")

#     # Set the project
#     !gcloud config set project {project_name}

#     # Enable Earth Engine API
#     !gcloud services enable earthengine.googleapis.com

#     # Initialize Earth Engine with the project
#     ee.Initialize(project=project_name)

#     print(f"Successfully authenticated and initialized with project: {project_name}")

# # Run authentication
# try:
#     authenticate_and_initialize()
# except Exception as e:
#     print(f"Authentication failed: {str(e)}")

import ee
from google.colab import auth

# Quick verification of our setup
def verify_gee_setup():
    try:
        # Initialize with existing project
        ee.Initialize(project='landsat-colab')

        # Try a simple EE operation to verify everything works
        image = ee.Image('USGS/SRTMGL1_003')
        print("Earth Engine is working correctly!")

        # Print current project
        !gcloud config get-value project

        return True
    except Exception as e:
        print(f"Setup verification failed: {str(e)}")
        return False

# Run verification
verify_gee_setup()

# !pip install earthengine-api
# !pip install geemap
# !pip install geopandas

# LST CODE
import ee
import geemap
import ipywidgets as widgets
from IPython.display import display
from datetime import datetime

# Initialize Earth Engine
def initialize_gee():
    try:
        ee.Initialize(project='landsat-colab')
    except Exception as e:
        print(f"Error initializing Earth Engine: {str(e)}")
        raise e

def get_tamil_nadu_districts():
    india_districts = ee.FeatureCollection('FAO/GAUL/2015/level2')
    tn_districts = india_districts.filter(ee.Filter.eq('ADM1_NAME', 'Tamil Nadu'))
    return tn_districts

def get_lst_data(year, month, region, is_daytime=True):
    collection = ee.ImageCollection('MODIS/061/MOD11A1')

    # Set date range
    start_date = ee.Date.fromYMD(year, month, 1)
    end_date = start_date.advance(1, 'month')

    # Filter collection
    lst = collection.filterDate(start_date, end_date)

    # Select daytime or nighttime LST
    band = 'LST_Day_1km' if is_daytime else 'LST_Night_1km'
    lst = lst.select(band)

    # Convert to Celsius
    lst = lst.map(lambda img: img.multiply(0.02).subtract(273.15))

    # Calculate mean LST
    lst_mean = lst.mean()

    # Clip to selected region before calculating statistics
    lst_clipped = lst_mean.clip(region)

    # Calculate statistics for the specific region
    stats = lst_clipped.reduceRegion(
        reducer=ee.Reducer.minMax(),
        geometry=region.geometry(),
        scale=1000,
        maxPixels=1e9
    ).getInfo()

    band_name = lst_mean.bandNames().get(0).getInfo()
    temp_min = stats[f'{band_name}_min']
    temp_max = stats[f'{band_name}_max']

    return lst_mean, temp_min, temp_max

class TamilNaduAnalysis:
    def __init__(self):
        self.tn_districts = get_tamil_nadu_districts()
        self.district_names = self.tn_districts.aggregate_array('ADM2_NAME').getInfo()
        self.current_layers = []
        self.setup_widgets()

    def setup_widgets(self):
        self.year_dropdown = widgets.Dropdown(
            options=[2018, 2020, 2024],
            description='Year:',
            value=2024
        )

        self.month_dropdown = widgets.Dropdown(
            options=list(range(3, 7)),
            description='Month:',
            value=3
        )

        self.time_toggle = widgets.ToggleButtons(
            options=['Daytime', 'Nighttime'],
            description='Time:',
            value='Daytime'
        )

        self.district_dropdown = widgets.Dropdown(
            options=['All'] + sorted(self.district_names),
            description='District:',
            value='All'
        )

        self.layer_toggle = widgets.ToggleButtons(
            options=['LST'],
            description='Layer:',
            value='LST'
        )

        self.analyze_button = widgets.Button(description='Analyze Data')
        self.analyze_button.on_click(self.update_map)

        display(widgets.VBox([
            self.year_dropdown,
            self.month_dropdown,
            self.time_toggle,
            self.district_dropdown,
            self.layer_toggle,
            self.analyze_button
        ]))

        self.map = geemap.Map(center=[11.1271, 78.6569], zoom=7)
        display(self.map)

    def clear_layers(self):
        try:
            self.map.layers = self.map.layers[:1]
            self.current_layers = []
            # Remove existing colorbars
            if hasattr(self.map, 'colorbar') and self.map.colorbar is not None:
                self.map.colorbar.close()
        except Exception as e:
            print(f"Error clearing layers: {str(e)}")

    def update_map(self, _):
        self.clear_layers()

        # Get region based on selection
        if self.district_dropdown.value == 'All':
            region = self.tn_districts
            display_name = "Tamil Nadu"
        else:
            region = self.tn_districts.filter(
                ee.Filter.eq('ADM2_NAME', self.district_dropdown.value)
            )
            display_name = self.district_dropdown.value

        # Add LST if selected
        if self.layer_toggle.value in ['LST']:
            # Get LST data for the specific region
            lst, temp_min, temp_max = get_lst_data(
                self.year_dropdown.value,
                self.month_dropdown.value,
                region,
                self.time_toggle.value == 'Daytime'
            )

            # Clip LST to the selected region
            lst_clipped = lst.clip(region)

            # Choose palette and create visualization parameters for the specific region
            viz_params_day = {
                'min': temp_min,
                'max': temp_max,
                'palette': ['blue', 'yellow', 'red']
            }
            viz_params_night = {
                'min': temp_min,
                'max': temp_max,
                'palette': ['navy', 'purple', 'cyan']
            }
            viz_params = viz_params_day if self.time_toggle.value == 'Daytime' else viz_params_night

            # Add LST layer
            lst_layer = geemap.ee_tile_layer(lst_clipped, viz_params, 'LST')
            self.map.add_layer(lst_layer)
            self.current_layers.append(lst_layer)

            # Add colorbar with region-specific range
            self.map.add_colorbar(
                viz_params,
                f'LST ({self.time_toggle.value}) for {display_name} (°C)'
            )

            # Calculate and print statistics for the specific region
            stats = lst_clipped.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=region.geometry(),
                scale=1000,
                maxPixels=1e9
            ).getInfo()

            print(f"\nLST Statistics for {display_name}:")
            print(f"Average Temperature: {stats[lst.bandNames().get(0).getInfo()]:.2f}°C")
            print(f"Temperature Range: {temp_min:.2f}°C to {temp_max:.2f}°C")

        # Add district boundaries
        district_style = {'color': 'black', 'fillColor': '00000000', 'width': 1}
        if self.district_dropdown.value == 'All':
            # For all districts, show all boundaries
            district_layer = geemap.ee_tile_layer(
                self.tn_districts.style(**district_style),
                {},
                'District Boundaries'
            )
        else:
            # For single district, highlight selected district
            district_layer = geemap.ee_tile_layer(
                region.style(**{**district_style, 'width': 2}),
                {},
                'Selected District'
            )

        self.map.add_layer(district_layer)
        self.current_layers.append(district_layer)

# Function to run the analysis
def run_analysis():
    analysis = TamilNaduAnalysis()
    return analysis

# Run the analysis when in Google Colab
if __name__ == "__main__":
    initialize_gee()
    analysis = run_analysis()

#LULC CODE
import ee
import folium

# Initialize the Earth Engine library.
def initialize_gee():
    try:
        ee.Initialize(project='landsat-colab')
    except Exception as e:
        print(f"Error initializing Earth Engine: {str(e)}")
        raise e

# Load the MODIS LULC dataset.
lulc = ee.Image('MODIS/006/MCD12Q1/2020_01_01').select('LC_Type1')

# Define a visualization palette for LULC with corresponding types.
lulc_vis_params = {
    'min': 1,
    'max': 17,
    'palette': [
        '05450a', '086a10', '54a708', '78d203', '009900', 'c6b044',
        'dcd159', 'dade48', 'fbff13', 'b6ff05', '27ff87', 'c24f44',
        'a5a5a5', 'ff6d4c', '69fff8', 'f9ffa4', '1c0dff'
    ]
}

# Load Tamil Nadu state boundary (example GADM dataset).
tamil_nadu_boundary = ee.FeatureCollection("FAO/GAUL/2015/level1").filter(
    ee.Filter.eq('ADM1_NAME', 'Tamil Nadu')
)

# Load Tamil Nadu district boundaries (example GADM dataset).
district_boundaries = ee.FeatureCollection("FAO/GAUL/2015/level2").filter(
    ee.Filter.eq('ADM1_NAME', 'Tamil Nadu')
)

# Define styles for boundaries with a black outline (no fill).
state_boundary_style = {'color': 'black', 'fillOpacity': 0, 'weight': 2}
district_boundary_style = {'color': 'black', 'fillOpacity': 0, 'weight': 1}

# Center the map on Tamil Nadu.
center_lat, center_lon = 11.1271, 78.6569
map_lulc = folium.Map(location=[center_lat, center_lon], zoom_start=6)

# Add the LULC layer.
def add_ee_layer(map_object, ee_image, vis_params, name):
    map_id_dict = ee.Image(ee_image).getMapId(vis_params)
    folium.TileLayer(
        tiles=map_id_dict['tile_fetcher'].url_format,
        attr="Map Data © Google Earth Engine",
        name=name,
        overlay=True,
        control=True
    ).add_to(map_object)

add_ee_layer(map_lulc, lulc, lulc_vis_params, 'LULC')

# Add Tamil Nadu boundary with only outlines (no fill).
def add_boundary_layer(map_object, ee_feature, style, name):
    map_id_dict = ee.FeatureCollection(ee_feature).style(
        **{'color': style['color'], 'fillColor': '00000000', 'width': style['weight']}
    ).getMapId()
    folium.TileLayer(
        tiles=map_id_dict['tile_fetcher'].url_format,
        attr="Map Data © Google Earth Engine",
        name=name,
        overlay=True,
        control=True
    ).add_to(map_object)

add_boundary_layer(map_lulc, tamil_nadu_boundary, state_boundary_style, "Tamil Nadu Boundary")
add_boundary_layer(map_lulc, district_boundaries, district_boundary_style, "District Boundaries")

# Add a layer control panel to toggle layers.
folium.LayerControl().add_to(map_lulc)

# Add legend for LULC classes.
legend_html = '''
<div style="position: fixed;
            bottom: 10px; left: 10px; width: 250px; height: 400px;
            background-color: white; z-index: 1000; font-size: 14px;
            border:2px solid grey; padding: 10px;">
<b>Land Cover Legend:</b><br>
1. <span style="color:#05450a;">&#9632;</span> Evergreen Needleleaf Forest<br>
2. <span style="color:#086a10;">&#9632;</span> Evergreen Broadleaf Forest<br>
3. <span style="color:#54a708;">&#9632;</span> Deciduous Needleleaf Forest<br>
4. <span style="color:#78d203;">&#9632;</span> Deciduous Broadleaf Forest<br>
5. <span style="color:#009900;">&#9632;</span> Mixed Forests<br>
6. <span style="color:#c6b044;">&#9632;</span> Closed Shrublands<br>
7. <span style="color:#dcd159;">&#9632;</span> Open Shrublands<br>
8. <span style="color:#dade48;">&#9632;</span> Woody Savannas<br>
9. <span style="color:#fbff13;">&#9632;</span> Savannas<br>
10. <span style="color:#b6ff05;">&#9632;</span> Grasslands<br>
11. <span style="color:#27ff87;">&#9632;</span> Permanent Wetlands<br>
12. <span style="color:#c24f44;">&#9632;</span> Croplands<br>
13. <span style="color:#a5a5a5;">&#9632;</span> Urban and Built-Up<br>
14. <span style="color:#ff6d4c;">&#9632;</span> Cropland/Natural Vegetation Mosaic<br>
15. <span style="color:#69fff8;">&#9632;</span> Snow and Ice<br>
16. <span style="color:#f9ffa4;">&#9632;</span> Barren or Sparsely Vegetated<br>
17. <span style="color:#1c0dff;">&#9632;</span> Water Bodies<br>
</div>
'''
map_lulc.get_root().html.add_child(folium.Element(legend_html))

# Display the map.
map_lulc

#LULC DONUT CHART
import ee
import pandas as pd
import plotly.graph_objects as go
from collections import defaultdict

def create_lulc_donut_chart(lulc_image, region):
    """
    Creates a donut chart showing the distribution of land use / land cover classes

    Parameters:
    lulc_image: ee.Image - The MODIS LULC image
    region: ee.Feature - The region of interest (e.g., Tamil Nadu boundary)
    """
    # Define LULC classes and their colors
    lulc_classes = {
        1: {'name': 'Evergreen Needleleaf Forest', 'color': '#05450a'},
        2: {'name': 'Evergreen Broadleaf Forest', 'color': '#086a10'},
        3: {'name': 'Deciduous Needleleaf Forest', 'color': '#54a708'},
        4: {'name': 'Deciduous Broadleaf Forest', 'color': '#78d203'},
        5: {'name': 'Mixed Forests', 'color': '#009900'},
        6: {'name': 'Closed Shrublands', 'color': '#c6b044'},
        7: {'name': 'Open Shrublands', 'color': '#dcd159'},
        8: {'name': 'Woody Savannas', 'color': '#dade48'},
        9: {'name': 'Savannas', 'color': '#fbff13'},
        10: {'name': 'Grasslands', 'color': '#b6ff05'},
        11: {'name': 'Permanent Wetlands', 'color': '#27ff87'},
        12: {'name': 'Croplands', 'color': '#c24f44'},
        13: {'name': 'Urban and Built-Up', 'color': '#a5a5a5'},
        14: {'name': 'Cropland/Natural Vegetation Mosaic', 'color': '#ff6d4c'},
        15: {'name': 'Snow and Ice', 'color': '#69fff8'},
        16: {'name': 'Barren or Sparsely Vegetated', 'color': '#f9ffa4'},
        17: {'name': 'Water Bodies', 'color': '#1c0dff'}
    }

    # Calculate area for each class
    area_stats = lulc_image.reduceRegion(
        reducer=ee.Reducer.frequencyHistogram(),
        geometry=region.geometry(),
        scale=500,
        maxPixels=1e9
    ).getInfo()

    # Process the statistics
    hist = area_stats['LC_Type1']
    total_pixels = sum(hist.values())

    # Create lists for plotting
    values = []
    labels = []
    colors = []
    custom_data = []  # For hover text

    # Sort by percentage (descending) to highlight major categories
    sorted_data = sorted([(k, v) for k, v in hist.items()],
                        key=lambda x: x[1],
                        reverse=True)

    for class_id, pixel_count in sorted_data:
        percentage = (pixel_count / total_pixels) * 100
        if percentage > 0.1:  # Only show classes with >0.1% coverage
            class_info = lulc_classes[int(class_id)]
            values.append(percentage)
            labels.append(class_info['name'])
            colors.append(class_info['color'])
            custom_data.append(f"{percentage:.1f}%")

    # Create the donut chart with improved label positioning
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.4,
        marker_colors=colors,
        textposition='outside',
        textinfo='label+percent',
        hovertemplate="%{label}<br>%{customdata}<extra></extra>",
        customdata=custom_data,
        rotation=90,
        pull=[0.1 if i < 3 else 0 for i in range(len(values))],  # Pull out larger segments
        textfont={'size': 11},  # Slightly smaller font size
        insidetextorientation='horizontal'
    )])

    # Update layout with more space for labels
    fig.update_layout(
        title={
            'text': 'Land Use / Land Cover Distribution in Tamil Nadu',
            'y': 0.98,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': {'size': 20}
        },
        showlegend=True,
        legend={
            'orientation': 'v',
            'yanchor': 'middle',
            'y': 0.5,
            'xanchor': 'left',
            'x': 1.2,  # Moved legend further right
            'font': {'size': 12}
        },
        width=1200,  # Increased width
        height=900,  # Increased height
        margin=dict(t=120, l=150, r=350, b=150),  # Increased margins all around
        annotations=[
            dict(
                text="",
                x=0.5,
                y=0.5,
                font=dict(size=20),
                showarrow=False
            )
        ]
    )

    return fig

# Usage example:
def display_lulc_distribution():
    # Initialize Earth Engine
    ee.Initialize(project='landsat-colab')

    # Load the MODIS LULC dataset
    lulc = ee.Image('MODIS/006/MCD12Q1/2020_01_01').select('LC_Type1')

    # Load Tamil Nadu boundary
    tamil_nadu = ee.FeatureCollection("FAO/GAUL/2015/level1").filter(
        ee.Filter.eq('ADM1_NAME', 'Tamil Nadu')
    ).first()

    # Create and display the chart
    fig = create_lulc_donut_chart(lulc, tamil_nadu)
    fig.show()

# Run the visualization
display_lulc_distribution()

# LST TIME SERIES CHART
import ee
import geemap
import ipywidgets as widgets
from IPython.display import display
import plotly.graph_objects as go
import plotly.io as pio
pio.renderers.default = 'colab'

# Initialize Earth Engine
def initialize_gee():
    try:
        ee.Initialize(project='landsat-colab')
    except Exception as e:
        print(f"Error initializing Earth Engine: {str(e)}")
        raise e

# Function to get Tamil Nadu districts
def get_tamil_nadu_districts():
    india_districts = ee.FeatureCollection('FAO/GAUL/2015/level2')
    tn_districts = india_districts.filter(ee.Filter.eq('ADM1_NAME', 'Tamil Nadu'))
    return tn_districts

# Function to get LST data for a specific date range and region
def get_lst_time_series(year, region, is_daytime=True):
    collection = ee.ImageCollection('MODIS/061/MOD11A1')

    # Set date range (March 1st to June 30th)
    start_date = ee.Date.fromYMD(year, 3, 1)
    end_date = ee.Date.fromYMD(year, 6, 30)

    # Filter collection by date
    lst = collection.filterDate(start_date, end_date)

    # Select daytime or nighttime LST
    band = 'LST_Day_1km' if is_daytime else 'LST_Night_1km'
    lst = lst.select(band)

    # Convert to Celsius
    lst = lst.map(lambda img: img.multiply(0.02).subtract(273.15))

    # Add system:time_start property by parsing system:index
    def add_time_start(image):
        # Extract the date string from system:index (e.g., "2020_03_01")
        date_string = image.get('system:index')
        # Parse the date string into a valid format (YYYY-MM-DD)
        date = ee.Date.parse('YYYY_MM_dd', date_string)
        # Set the system:time_start property
        return image.set('system:time_start', date.millis())

    lst = lst.map(add_time_start)

    # Clip to selected region
    lst = lst.map(lambda img: img.clip(region))

    return lst

# Function to extract time series data
def extract_time_series(lst_collection, region):
    def extract_mean_lst(image):
        date = image.date().format('YYYY-MM-dd')
        mean_lst = image.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=region.geometry(),
            scale=1000,
            maxPixels=1e9
        ).get(band)
        return ee.Feature(None, {'date': date, 'mean_lst': mean_lst})

    band = lst_collection.first().bandNames().get(0)
    time_series = lst_collection.map(extract_mean_lst)
    return time_series

# Function to plot time series using Plotly
def plot_time_series(time_series, title):
    # Extract features and filter out invalid ones
    features = time_series.getInfo()['features']
    print(f"Total features: {len(features)}")  # Debug: Print total features

    valid_features = [
        item for item in features
        if 'mean_lst' in item['properties'] and item['properties']['mean_lst'] is not None
    ]
    print(f"Valid features: {len(valid_features)}")  # Debug: Print valid features

    if not valid_features:
        print("No valid data to plot. Check if the region or date range has valid LST data.")
        return

    # Extract dates and mean_lst values
    dates = [item['properties']['date'] for item in valid_features]
    mean_lst = [item['properties']['mean_lst'] for item in valid_features]

    # Debug: Print the first few dates and mean_lst values
    print("Sample dates:", dates[:5])
    print("Sample mean_lst:", mean_lst[:5])

    # Create Plotly figure
    fig = go.Figure()

    # Add trace for the time series
    fig.add_trace(go.Scatter(
        x=dates,
        y=mean_lst,
        mode='lines+markers',
        name='Mean LST',
        hoverinfo='x+y',
        line=dict(color='blue'),
        marker=dict(color='blue', size=8)
    ))

    # Update layout for better readability
    fig.update_layout(
        title=title,
        xaxis_title='Date',
        yaxis_title='Mean LST (°C)',
        hovermode='x unified',  # Show hover info for all traces at the same x-value
        xaxis=dict(
            tickangle=45,  # Rotate x-axis labels for better readability
            tickformat='%Y-%m-%d',  # Format dates as YYYY-MM-DD
            showgrid=True,
            gridcolor='lightgray'
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='lightgray'
        ),
        template='plotly_white'  # Use a clean template
    )

    # Show the figure
    fig.show()

# Class for Time Series Analysis
class TamilNaduTimeSeriesAnalysis:
    def __init__(self):
        self.tn_districts = get_tamil_nadu_districts()
        self.district_names = self.tn_districts.aggregate_array('ADM2_NAME').getInfo()
        self.setup_widgets()

    def setup_widgets(self):
        self.year_dropdown = widgets.Dropdown(
            options=[2018, 2020, 2024],
            description='Year:',
            value=2024
        )

        self.time_toggle = widgets.ToggleButtons(
            options=['Daytime', 'Nighttime'],
            description='Time:',
            value='Daytime'
        )

        self.district_dropdown = widgets.Dropdown(
            options=['All'] + sorted(self.district_names),
            description='District:',
            value='All'
        )

        self.plot_button = widgets.Button(description='Plot Time Series')
        self.plot_button.on_click(self.plot_time_series)

        display(widgets.VBox([
            self.year_dropdown,
            self.time_toggle,
            self.district_dropdown,
            self.plot_button
        ]))

    def plot_time_series(self, _):
        # Get region based on selection
        if self.district_dropdown.value == 'All':
            region = self.tn_districts
            display_name = "Tamil Nadu"
        else:
            region = self.tn_districts.filter(
                ee.Filter.eq('ADM2_NAME', self.district_dropdown.value)
            )
            display_name = self.district_dropdown.value

        # Get LST time series data
        lst_collection = get_lst_time_series(
            self.year_dropdown.value,
            region,
            self.time_toggle.value == 'Daytime'
        )

        # Extract time series data
        time_series = extract_time_series(lst_collection, region)

        # Plot time series
        title = f"LST Time Series ({self.time_toggle.value}) for {display_name} ({self.year_dropdown.value})"
        plot_time_series(time_series, title)

# Function to run the time series analysis
def run_time_series_analysis():
    analysis = TamilNaduTimeSeriesAnalysis()
    return analysis

# Run the analysis when in Google Colab
if __name__ == "__main__":
    initialize_gee()
    analysis = run_time_series_analysis()

# LST comparison of 2 difference map
import ee
import geemap
import ipywidgets as widgets
from IPython.display import display

# Initialize Earth Engine
def initialize_gee():
    try:
        ee.Initialize(project='landsat-colab')
    except Exception as e:
        print(f"Error initializing Earth Engine: {str(e)}")
        raise e

# Function to get Tamil Nadu districts
def get_tamil_nadu_districts():
    india_districts = ee.FeatureCollection('FAO/GAUL/2015/level2')
    tn_districts = india_districts.filter(ee.Filter.eq('ADM1_NAME', 'Tamil Nadu'))
    return tn_districts

# Function to get LST data for a specific date range and region
def get_lst_time_series(year, region, is_daytime=True):
    collection = ee.ImageCollection('MODIS/061/MOD11A1')

    # Set date range (March 1st to June 30th)
    start_date = ee.Date.fromYMD(year, 3, 1)
    end_date = ee.Date.fromYMD(year, 6, 30)

    # Filter collection by date
    lst = collection.filterDate(start_date, end_date)

    # Select daytime or nighttime LST
    band = 'LST_Day_1km' if is_daytime else 'LST_Night_1km'
    lst = lst.select(band)

    # Convert to Celsius
    lst = lst.map(lambda img: img.multiply(0.02).subtract(273.15))

    # Add system:time_start property by parsing system:index
    def add_time_start(image):
        # Extract the date string from system:index (e.g., "2020_03_01")
        date_string = image.get('system:index')
        # Parse the date string into a valid format (YYYY-MM-DD)
        date = ee.Date.parse('YYYY_MM_dd', date_string)
        # Set the system:time_start property
        return image.set('system:time_start', date.millis())

    lst = lst.map(add_time_start)

    # Clip to selected region
    lst = lst.map(lambda img: img.clip(region))

    return lst

# Function to compute and display the difference map
def plot_difference_map(year_1, year_2, region, is_daytime=True):
    # Get LST data for Year 1
    lst_collection_1 = get_lst_time_series(year_1, region, is_daytime)
    lst_mean_1 = lst_collection_1.mean()

    # Get LST data for Year 2
    lst_collection_2 = get_lst_time_series(year_2, region, is_daytime)
    lst_mean_2 = lst_collection_2.mean()

    # Compute the difference (Year 2 - Year 1)
    lst_diff = lst_mean_2.subtract(lst_mean_1)

    # Clip to the selected region
    lst_diff_clipped = lst_diff.clip(region)

    # Visualize the difference map
    viz_params = {
        'min': -10,  # Minimum difference
        'max': 10,   # Maximum difference
        'palette': ['blue', 'white', 'red']  # Blue for negative, white for no change, red for positive
    }

    # Create a map
    map_diff = geemap.Map()
    map_diff.add_layer(lst_diff_clipped, viz_params, 'LST Difference')
    map_diff.add_layer(region.style(**{'color': 'black', 'fillColor': '00000000'}), {}, 'Region')
    map_diff.setCenter(78.6569, 11.1271, 7)  # Center on Tamil Nadu
    display(map_diff)

# Class for Difference Map Comparison
class TamilNaduDifferenceMapAnalysis:
    def __init__(self):
        self.tn_districts = get_tamil_nadu_districts()
        self.district_names = self.tn_districts.aggregate_array('ADM2_NAME').getInfo()
        self.setup_widgets()

    def setup_widgets(self):
        # Dropdown for Year 1
        self.year_dropdown_1 = widgets.Dropdown(
            options=[2018, 2020, 2024],
            description='Year 1:',
            value=2018
        )

        # Dropdown for Year 2
        self.year_dropdown_2 = widgets.Dropdown(
            options=[2018, 2020, 2024],
            description='Year 2:',
            value=2020
        )

        # Toggle for Time (Daytime/Nighttime)
        self.time_toggle = widgets.ToggleButtons(
            options=['Daytime', 'Nighttime'],
            description='Time:',
            value='Daytime'
        )

        # Dropdown for District
        self.district_dropdown = widgets.Dropdown(
            options=['All'] + sorted(self.district_names),
            description='District:',
            value='All'
        )

        # Button to plot difference map
        self.plot_button = widgets.Button(description='Plot Difference Map')
        self.plot_button.on_click(self.plot_difference_map)

        # Display widgets
        display(widgets.VBox([
            self.year_dropdown_1,
            self.year_dropdown_2,
            self.time_toggle,
            self.district_dropdown,
            self.plot_button
        ]))

    def plot_difference_map(self, _):
        # Get region based on selection
        if self.district_dropdown.value == 'All':
            region = self.tn_districts
            display_name = "Tamil Nadu"
        else:
            region = self.tn_districts.filter(
                ee.Filter.eq('ADM2_NAME', self.district_dropdown.value)
            )
            display_name = self.district_dropdown.value

        # Plot difference map
        plot_difference_map(
            self.year_dropdown_1.value,
            self.year_dropdown_2.value,
            region,
            self.time_toggle.value == 'Daytime'
        )

# Function to run the difference map analysis
def run_difference_map_analysis():
    analysis = TamilNaduDifferenceMapAnalysis()
    return analysis

# Run the analysis when in Google Colab
if __name__ == "__main__":
    initialize_gee()
    analysis = run_difference_map_analysis()


# Blue Areas: Regions where LST in Year 2 is cooler than in Year 1.

# Red Areas: Regions where LST in Year 2 is warmer than in Year 1.

# White Areas: Regions with no significant change in LST.

import ee
import geemap
import ipywidgets as widgets
from IPython.display import display, clear_output
import plotly.express as px
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
import time

# Initialize Earth Engine
def initialize_gee():
    try:
        ee.Initialize(project='landsat-colab')
    except Exception as e:
        print(f"Error initializing Earth Engine: {str(e)}")
        raise e

# Function to get Tamil Nadu districts
def get_tamil_nadu_districts():
    india_districts = ee.FeatureCollection('FAO/GAUL/2015/level2')
    tn_districts = india_districts.filter(ee.Filter.eq('ADM1_NAME', 'Tamil Nadu'))
    return tn_districts

# Function to get LST data from MODIS
def get_lst_time_series(year, region, is_daytime=True):
    # Load MODIS LST collection
    collection = ee.ImageCollection('MODIS/061/MOD11A1')

    # Set date range (March 1st to June 30th)
    start_date = ee.Date.fromYMD(year, 3, 1)
    end_date = ee.Date.fromYMD(year, 6, 30)

    # Filter collection by date
    lst = collection.filterDate(start_date, end_date)

    # Select daytime or nighttime LST
    band = 'LST_Day_1km' if is_daytime else 'LST_Night_1km'
    lst = lst.select(band)

    # Convert to Celsius
    lst = lst.map(lambda img: img.multiply(0.02).subtract(273.15))

    # Add system:time_start property by parsing system:index
    def add_time_start(image):
        # Extract the date string from system:index (e.g., "2020_03_01")
        date_string = image.get('system:index')
        # Parse the date string into a valid format (YYYY-MM-DD)
        date = ee.Date.parse('YYYY_MM_dd', date_string)
        # Set the system:time_start property
        return image.set('system:time_start', date.millis())

    lst = lst.map(add_time_start)

    # Clip to selected region
    lst = lst.map(lambda img: img.clip(region))

    return lst

# Function to extract time series data
def extract_time_series(lst_collection, region, selected_year):
    def extract_lst(image):
        # Get the date from the image
        date_millis = image.get('system:time_start')
        date = ee.Date(date_millis).format('YYYY-MM-dd')

        # Get all pixel values
        lst_values = image.reduceRegion(
            reducer=ee.Reducer.toList(),
            geometry=region.geometry(),
            scale=1000,  # MODIS resolution is 1km
            maxPixels=1e9
        ).get(band)

        return ee.Feature(None, {
            'date': date,
            'lst_values': lst_values,
            'year': selected_year  # Add the selected year explicitly
        })

    band = lst_collection.first().bandNames().get(0)
    time_series = lst_collection.map(extract_lst)
    return time_series

# Function to plot side-by-side comparison bar chart
def plot_side_by_side_comparison(time_series_1, time_series_2, title, year1, year2):
    # Extract features for both time series
    features_1 = time_series_1.getInfo()['features']
    features_2 = time_series_2.getInfo()['features']

    # Create dictionaries to store aggregated data for each date
    data_dict_1 = {}
    data_dict_2 = {}

    # Process Year 1 data
    for feature in features_1:
        date = feature['properties']['date']
        if 'lst_values' in feature['properties'] and feature['properties']['lst_values']:
            values = [float(temp) for temp in feature['properties']['lst_values'] if temp is not None]
            if values:
                # Keep the original date format but create month-day for sorting
                original_date = datetime.strptime(date, '%Y-%m-%d')
                month_day = original_date.strftime('%m-%d')
                data_dict_1[month_day] = {
                    'temp': sum(values) / len(values),  # average temperature
                    'full_date': date,
                    'display_date': original_date.strftime(f'%b %d, {year1}')
                }

    # Process Year 2 data
    for feature in features_2:
        date = feature['properties']['date']
        if 'lst_values' in feature['properties'] and feature['properties']['lst_values']:
            values = [float(temp) for temp in feature['properties']['lst_values'] if temp is not None]
            if values:
                # Keep the original date format but create month-day for sorting
                original_date = datetime.strptime(date, '%Y-%m-%d')
                month_day = original_date.strftime('%m-%d')
                data_dict_2[month_day] = {
                    'temp': sum(values) / len(values),  # average temperature
                    'full_date': date,
                    'display_date': original_date.strftime(f'%b %d, {year2}')
                }

    # Create list of all dates
    all_dates = sorted(list(set(data_dict_1.keys()) | set(data_dict_2.keys())))

    # Create DataFrame for side-by-side chart
    data = []
    for date in all_dates:
        if date in data_dict_1:
            data.append({
                'Date': date,
                'Display_Date': data_dict_1[date]['display_date'],
                'Temperature': min(data_dict_1[date]['temp'], 80),  # Limit to 80 degrees
                'Year': str(year1)
            })
        if date in data_dict_2:
            data.append({
                'Date': date,
                'Display_Date': data_dict_2[date]['display_date'],
                'Temperature': min(data_dict_2[date]['temp'], 80),  # Limit to 80 degrees
                'Year': str(year2)
            })

    df = pd.DataFrame(data)

    # Create the figure
    fig = px.bar(
        df,
        x='Date',
        y='Temperature',
        color='Year',
        barmode='group',
        title=title,
        labels={'Temperature': 'Temperature (°C)'},
        color_discrete_map={str(year1): 'rgb(55, 83, 109)', str(year2): 'rgb(26, 118, 255)'},
        custom_data=['Display_Date']  # Add custom data for hover
    )

    # Update layout
    fig.update_layout(
        yaxis=dict(
            title='Temperature (°C)',
            tickformat='.1f',
            range=[0, 60]  # Set fixed y-axis range from 0 to 60
        ),
        xaxis=dict(
            title='Date',
            tickangle=45,
            tickmode='array',
            tickvals=all_dates[::7],  # Show every 7th date to reduce clutter
            ticktext=[datetime.strptime(d, '%m-%d').strftime('%b %d') for d in all_dates[::7]]  # Convert to nicer format
        ),
        bargap=0.2,
        template='plotly_white',
        height=600,
        width=1200,
        showlegend=True,
        legend=dict(
            x=0.01,
            y=0.99,
            bgcolor='rgba(255, 255, 255, 0.8)'
        )
    )

    # Update hover template to use the display date
    fig.update_traces(
        hovertemplate='<b>%{customdata}</b><br>Temperature: %{y:.1f}°C<extra></extra>'
    )

    # Show the figure
    fig.show()
    return fig

# Class for Side-by-Side Comparison Analysis
class TamilNaduSideBySideComparisonAnalysis:
    def __init__(self):
        self.tn_districts = get_tamil_nadu_districts()
        self.district_names = self.tn_districts.aggregate_array('ADM2_NAME').getInfo()
        self.setup_widgets()
        self.output = widgets.Output()
        display(self.output)

    def setup_widgets(self):
        # Dropdown for Year 1
        self.year_dropdown_1 = widgets.Dropdown(
            options=[2018, 2020, 2024],
            description='Year 1:',
            value=2018
        )

        # Dropdown for Year 2
        self.year_dropdown_2 = widgets.Dropdown(
            options=[2018, 2020, 2024],
            description='Year 2:',
            value=2020
        )

        # Toggle for Daytime/Nighttime
        self.time_toggle = widgets.ToggleButtons(
            options=['Daytime', 'Nighttime'],
            description='Time:',
            value='Daytime'
        )

        # Dropdown for District
        self.district_dropdown = widgets.Dropdown(
            options=['All'] + sorted(self.district_names),
            description='District:',
            value='All'
        )

        # Loading indicator
        self.loading_indicator = widgets.HTML(
            value='<div style="display:none"><i>Loading data... please wait...</i></div>'
        )

        # Button to plot side-by-side comparison chart
        self.plot_button = widgets.Button(description='Plot Comparison')
        self.plot_button.on_click(self.handle_plot_button)

        # Display widgets
        display(widgets.VBox([
            self.year_dropdown_1,
            self.year_dropdown_2,
            self.time_toggle,
            self.district_dropdown,
            self.loading_indicator,
            self.plot_button
        ]))

    def show_loading(self, is_loading=True):
        if is_loading:
            self.loading_indicator.value = '<div><i>Loading data... please wait...</i></div>'
        else:
            self.loading_indicator.value = '<div style="display:none"><i>Loading data... please wait...</i></div>'

    def handle_plot_button(self, _):
        with self.output:
            clear_output(wait=True)
            self.show_loading(True)
            try:
                # Get selected years
                year1 = self.year_dropdown_1.value
                year2 = self.year_dropdown_2.value

                # Get region based on selection
                if self.district_dropdown.value == 'All':
                    region = self.tn_districts
                    display_name = "Tamil Nadu"
                else:
                    region = self.tn_districts.filter(
                        ee.Filter.eq('ADM2_NAME', self.district_dropdown.value)
                    )
                    display_name = self.district_dropdown.value

                # Get LST time series data for both years
                lst_collection_1 = get_lst_time_series(year1, region, self.time_toggle.value == 'Daytime')
                time_series_1 = extract_time_series(lst_collection_1, region, year1)

                lst_collection_2 = get_lst_time_series(year2, region, self.time_toggle.value == 'Daytime')
                time_series_2 = extract_time_series(lst_collection_2, region, year2)

                # Plot comparison chart
                title = f"Daily LST Comparison ({self.time_toggle.value}) for {display_name}: {year1} vs {year2}"
                fig = plot_side_by_side_comparison(time_series_1, time_series_2, title, year1, year2)

                # Slow down the rendering to prevent browser from freezing
                time.sleep(0.5)

            except Exception as e:
                print(f"Error generating plot: {str(e)}")
                import traceback
                traceback.print_exc()
            finally:
                self.show_loading(False)

# Function to run the analysis
def run_side_by_side_comparison_analysis():
    analysis = TamilNaduSideBySideComparisonAnalysis()
    return analysis

# Run the analysis when in Google Colab
if __name__ == "__main__":
    initialize_gee()
    analysis = run_side_by_side_comparison_analysis()

import ee
import folium
import ipywidgets as widgets
from IPython.display import display, HTML
import time

def initialize_gee():
    try:
        ee.Initialize(project='landsat-colab')
        print("Earth Engine initialized successfully")
    except Exception as e:
        print(f"Error initializing Earth Engine: {str(e)}")
        raise e

# Define LULC classes and temperature reduction techniques
lulc_classes = {
    1: "Evergreen Needleleaf Forest",
    2: "Evergreen Broadleaf Forest",
    3: "Deciduous Needleleaf Forest",
    4: "Deciduous Broadleaf Forest",
    5: "Mixed Forests",
    6: "Closed Shrublands",
    7: "Open Shrublands",
    8: "Woody Savannas",
    9: "Savannas",
    10: "Grasslands",
    11: "Permanent Wetlands",
    12: "Croplands",
    13: "Urban and Built-Up",
    14: "Cropland/Natural Vegetation Mosaic",
    15: "Snow and Ice",
    16: "Barren or Sparsely Vegetated",
    17: "Water Bodies"
}

temperature_reduction_techniques = {
    1: "Increase tree density and promote afforestation.",
    2: "Protect existing forests and reduce deforestation.",
    3: "Promote mixed-species plantations.",
    4: "Encourage deciduous tree planting in urban areas.",
    5: "Maintain mixed forest ecosystems.",
    6: "Restore shrublands and reduce land degradation.",
    7: "Implement soil conservation techniques.",
    8: "Promote agroforestry and sustainable land use.",
    9: "Restore grasslands and prevent overgrazing.",
    10: "Implement sustainable grazing practices.",
    11: "Protect wetlands and reduce drainage.",
    12: "Adopt precision agriculture and crop rotation.",
    13: "Increase green spaces and urban tree cover.",
    14: "Promote agroecological practices.",
    15: "Not applicable (Snow and Ice).",
    16: "Implement soil stabilization and re-vegetation.",
    17: "Protect water bodies and reduce pollution."
}

def load_datasets():
    try:
        # Load the MODIS LULC dataset - using correct asset ID
        lulc = ee.Image('MODIS/061/MCD12Q1/2020_01_01').select('LC_Type1')

        # Load and process LST data with a longer time range for better coverage
        lst_collection = ee.ImageCollection('MODIS/061/MOD11A1') \
            .filterDate('2020-01-01', '2020-12-31') \
            .select('LST_Day_1km')

        # Convert LST to Celsius
        lst_collection = lst_collection.map(lambda img:
            img.multiply(0.02).subtract(273.15))

        # Calculate mean LST
        mean_lst = lst_collection.mean()

        # Load district boundaries
        district_boundaries = ee.FeatureCollection("FAO/GAUL/2015/level2") \
            .filter(ee.Filter.eq('ADM1_NAME', 'Tamil Nadu'))

        return lulc, mean_lst, district_boundaries

    except Exception as e:
        print(f"Error loading datasets: {str(e)}")
        raise e

def create_map(district_boundaries, lulc):
    try:
        # Get the center of Tamil Nadu
        center_lat, center_lon = 11.1271, 78.6569

        # Create the map with custom dimensions
        m = folium.Map(location=[center_lat, center_lon], zoom_start=7, width='1000px', height='650px')

        # Add LULC layer
        lulc_vis_params = {
            'min': 1,
            'max': 17,
            'palette': [
                '05450a', '086a10', '54a708', '78d203', '009900', 'c6b044',
                'dcd159', 'dade48', 'fbff13', 'b6ff05', '27ff87', 'c24f44',
                'a5a5a5', 'ff6d4c', '69fff8', 'f9ffa4', '1c0dff'
            ]
        }

        # Get the LULC map ID and token
        lulc_mapid = ee.Image(lulc).getMapId(lulc_vis_params)

        # Add the LULC layer to the map
        folium.TileLayer(
            tiles=lulc_mapid['tile_fetcher'].url_format,
            attr='Google Earth Engine',
            name='Land Use/Land Cover'
        ).add_to(m)

        # Add district boundaries with hover tooltip for names
        district_features = district_boundaries.getInfo()['features']
        for district in district_features:
            folium.GeoJson(
                district,
                name=district['properties']['ADM2_NAME'],
                style_function=lambda x: {
                    'fillColor': 'transparent',
                    'color': 'black',
                    'weight': 1
                },
                tooltip=folium.Tooltip(district['properties']['ADM2_NAME'])
            ).add_to(m)

        # Add layer control
        folium.LayerControl().add_to(m)

        return m

    except Exception as e:
        print(f"Error creating map: {str(e)}")
        return None

def analyze_district(district, lulc, lst):
    try:
        # Get district geometry
        district_geom = district.geometry()

        # Clip datasets to district
        lulc_clipped = lulc.clip(district_geom)
        lst_clipped = lst.clip(district_geom)

        # Calculate mean LST for the district
        lst_mean = lst_clipped.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=district_geom,
            scale=500,
            maxPixels=1e9
        )

        # Create a mask for each LULC class and calculate mean LST
        results = []
        for lulc_class in lulc_classes.keys():
            # Create mask for current LULC class
            class_mask = lulc_clipped.eq(lulc_class)
            masked_lst = lst_clipped.updateMask(class_mask)

            # Calculate mean LST for this class
            class_stats = masked_lst.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=district_geom,
                scale=500,
                maxPixels=1e9
            )

            lst_value = class_stats.get('LST_Day_1km').getInfo()
            if lst_value is not None:
                results.append({
                    'lulc_class': lulc_class,
                    'mean': lst_value
                })

        return {
            'LST_Day_1km': lst_mean.get('LST_Day_1km').getInfo(),
            'groups': results
        }

    except Exception as e:
        print(f"Error in district analysis: {str(e)}")
        return None

def format_output(district_name, results):
    if not results:
        return "No data available for this district.\n", "No data available for this district."

    hover_output = f"LULC and LST for selected district:\nDistrict: {district_name}\n"
    printed_output = [
        f"Temperature Reduction Analysis for {district_name}:",
        "-" * 40
    ]

    print(f"LST Mean for {district_name}: {{'LST_Day_1km': {results['LST_Day_1km']}}}")
    print(f"LULC Stats for {district_name}: {{'groups': {results['groups']}}}")

    for result in results['groups']:
        lulc_class = result['lulc_class']
        mean_temp = result['mean']

        if lulc_class in lulc_classes:
            class_name = lulc_classes[lulc_class]

            # Update hover output
            if mean_temp is not None:
                hover_output += f"{class_name}: {mean_temp:.2f}°C\n"
            else:
                hover_output += f"{class_name}: No data\n"

            # Update printed output
            printed_output.append(f"LULC Class: {class_name}")
            if mean_temp is not None:
                printed_output.extend([
                    f"Mean LST: {mean_temp:.2f}°C",
                    f"Suggested Technique: {temperature_reduction_techniques[lulc_class]}"
                ])
            else:
                printed_output.append("LST data not found. Skipping temperature reduction calculation.")
            printed_output.append("-" * 40)

    return hover_output, "\n".join(printed_output)

def main():
    try:
        # Initialize Earth Engine
        initialize_gee()

        # Load datasets
        lulc, mean_lst, district_boundaries = load_datasets()

        # Create map
        m = create_map(district_boundaries, lulc)
        if m is None:
            print("Error: Could not create map")
            return

        # Create UI elements
        district_dropdown = widgets.Dropdown(
            options=sorted(district_boundaries.aggregate_array('ADM2_NAME').getInfo()),
            description='District:',
            layout=widgets.Layout(width='300px')
        )

        analyze_button = widgets.Button(
            description='Analyze District',
            button_style='primary',
            layout=widgets.Layout(width='200px')
        )

        output_area = widgets.Output()
        loading_label = widgets.Label(value="Fetching data...")

        def on_analyze_click(b):
            output_area.clear_output()
            display(loading_label)  # Show loading indicator

            with output_area:
                try:
                    # Get selected district
                    selected_district = district_boundaries.filter(
                        ee.Filter.eq('ADM2_NAME', district_dropdown.value)
                    ).first()

                    # Perform analysis
                    results = analyze_district(selected_district, lulc, mean_lst)

                    if results:
                        hover_output, printed_output = format_output(district_dropdown.value, results)
                        print(hover_output)
                        print("\nPrinted Analysis:")
                        print("-" * 40)
                        print(printed_output)
                    else:
                        print(f"No data available for {district_dropdown.value}")

                except Exception as e:
                    print(f"Error during analysis: {str(e)}")
                finally:
                    loading_label.value = ""  # Hide loading indicator

        # Connect button click handler
        analyze_button.on_click(on_analyze_click)

        # Display UI elements
        display(HTML("<h2>Tamil Nadu Land Use and Temperature Analysis</h2>"))
        display(m)
        display(widgets.VBox([district_dropdown, analyze_button, output_area]))



    except Exception as e:
        print(f"Error in main execution: {str(e)}")
        raise e

if __name__ == "__main__":
    main()
