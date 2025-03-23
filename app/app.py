from faicons import icon_svg
import faicons as fa
import plotly.express as px
import pandas as pd
from ipyleaflet import Map, basemaps, Marker, Popup, MarkerCluster

from maplibre import (
    Layer,
    LayerType,
    Map,
    MapOptions,
    output_maplibregl,
    render_maplibregl,
)
from maplibre.basemaps import Carto
from maplibre.controls import (
    Marker,
    MarkerOptions,
    NavigationControl,
    Popup,
    PopupOptions,
)
from maplibre.sources import GeoJSONSource
from maplibre.utils import GeometryType, df_to_geojson

from shiny import App, reactive, render, ui

from shinywidgets import render_widget, output_widget, render_plotly
from shinyswatch import theme

# Load data and compute static values
from shared import app_dir, grants, grant_total, grant_areas, grant_range, get_color, BOUNDS

# create the list for subtypes filter
# create list of subtypes based on filter types
grant_subtypes = list(grants["Subtype"].dropna().unique())
grant_subtypes.append("All")
grant_subtypes.sort()


ui.tags.style(".navbar.navbar-static-top { background:#78c2ad; }")

app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.input_slider(
            "grant_amount",
            "Grant amount",
            min=grant_range[0],
            max=grant_range[1],
            value=grant_range,
            pre="GBP ",
        ),

    ui.input_checkbox_group(
        "lc_dedicated",
        "Dedicated to Long Covid",
        {"Yes":"Completely", "Partially": "Partially", "No": "No, wrongly tagged 'Long Covid'"},
        selected=["Yes","Partially","No"],
        inline=True,
        ),
    
    ui.input_checkbox_group(
        "datasource",
        "Data Source",
        {"Grantnav":"360Giving GrantNav","NIHR":"NIHR", "UKCDR":"UKCDR"},
        selected=["Grantnav","NIHR","UKCDR"],
        inline=True,
    ),

    ui.input_selectize(
        "grant_area", 
        "Select grant type", 
        choices=grant_areas, 
        selected="AA"),
    
    ui.input_selectize(
        "grant_subtype",
        "Select grant subtype", 
        choices=grant_subtypes, 
        selected="All"),

    ui.input_action_button(
        "reset", 
        "Reset filter", 
        style="color:white; "
        "background:#de4712"),

        title="Filters",
    ),


    # Top row value boxes
    ui.navset_card_pill(
        ui.nav_panel("Overview", 
                     ui.layout_column_wrap(
                         ui.value_box(
                             "Number of grants",
                             ui.output_text("grant_count"),
                             showcase=icon_svg("calculator")
                         ),
                        ui.value_box(
                            "GBP total for selected",
                            ui.output_ui("grant_sum"),
                            ui.output_ui("selected_percent"),
                            showcase=fa.icon_svg("piggy-bank"),

                        ),
                        ui.value_box(
                            "Number of organisations",
                            ui.output_ui("orgnumber"),
                            showcase=fa.icon_svg("house")

                        ),
                     fill=True,
                     ),                     
                    ),

              

        ui.nav_panel("Charts", 
                     "Panel B content"),
        
        ui.nav_panel("Datagrid", 
                     "Panel C content"),
        
        ui.nav_panel("Map", 
                     "Panel C content"),
        
        ui.nav_panel("Data Source", 
                     "Panel C content"),
        
        id="tab",  
    ), 

    title="Long Covid Grants",
    fillable=True,
    theme=theme.minty,
)

                    



# --------------------------------------------------------
# Reactive calculations and effects
# --------------------------------------------------------
def server(input, output, session):
    
    # Functions for tab "overview"
    @render.text
    def grant_count(): # number of grants in current filter selection
        return filtered_grants().shape[0]
    @render.express
    def grant_sum(): # GPB total of current filter selection
        d = filtered_grants()
        if d.shape[0] > 0:
            sum = d.Amnt_awa.sum()
            f"{sum:,.0f}"
    @render.express
    def selected_percent(): # How many percent of the total GBP in the current selection
        d = filtered_grants()
        if d.shape[0] > 0:
            perc = (d.Amnt_awa.sum()/grant_total)*100
            f"({perc:,.2f}% of total GBP)"
    @render.express
    def orgnumber():
        num = filtered_grants()["Organisation_name"].unique()
        len(num)
    
    @reactive.calc
    def filtered_grants():
        grantgbp = input.grant_amount()
        filt1 = grants["Amnt_awa"].between(grantgbp[0], grantgbp[1])

        grantarea = input.grant_area()
        for area in grant_areas.items():
            if area[0] == grantarea:
                filt2 = (grants["Type"] == area[1])
            elif grantarea == "AA":
                filt2 = (grants["Type"] != "AA")
        
        grantsub = input.grant_subtype()
        for sub in grant_subtypes:
            if sub == grantsub:
                filt5 = (grants["Subtype"] == sub)
            elif grantsub == "All":
                filt5 = (grants["Subtype"] != "All")


        filt3 = grants["LC_dedicated"].isin(input.lc_dedicated())
        filt4 = grants["Data_source"].isin(input.datasource())
        
        return pd.DataFrame(grants.loc[filt1 & filt2 & filt3 & filt4 &filt5,
                                    ["ID",
                                        "Data_source",
                                        "Identifier",
                                        "LC_dedicated",
                                        "Type","Subtype",
                                        "Amnt_awa",
                                        "Year_awa",
                                        "Title",
                                        "Recipient_postal", 
                                        "Organisation_name",
                                        "Year_org_reg",
                                        "Org_age",
                                        "Org_age_group",
                                        "Recipient_income_latest",
                                        "Income_group",
                                        "Description",
                                        "Recipient_datereg",
                                        "Recipient_orgtype",
                                        "lon",
                                        "lat",
                                        "coordinates"]])

    @reactive.effect
    @reactive.event(input.reset)
    def _():
        ui.update_slider("grant_amount", value=grant_range)
        ui.update_radio_buttons("lc_dedicated", selected=["Yes","No","Partially"])
        ui.update_selectize("grant_area",selected="AA")
        ui.update_selectize("grant_subtype",selected="All")
        ui.update_radio_buttons("datasource", selected=["Grantnav","NIHR", "UKCDR"])

app = App(app_ui, server)