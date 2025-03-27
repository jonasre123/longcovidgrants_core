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
from shared import app_dir, grants, grant_total, grant_areas, grant_range, BOUNDS, get_color

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

              
# Charts tab
        ui.nav_panel("Charts", 
                     ui.navset_card_pill(
                          ui.nav_panel("Grants awarded per year", 
                                       ui.layout_column_wrap(
                                           ui.card("For NIHR and UKCDR data, the start year of funding was substituted in place of the award year.",
                                                   output_widget("fig_grants_per_year")),
                                           ui.card("Sum (GBP) of grants awarded per year"),
                                           width=1/1),),
                          ui.nav_panel("Grant types and subtypes", 
                                       ui.layout_column_wrap(
                                           ui.card("Grant types"),
                                           ui.card("Grant subtypes, where available"),
                                           width=1/1),),
                          ui.nav_panel("Organisation age and latest income", 
                                       ui.layout_column_wrap(
                                           ui.card("Grants awarded by organisation age & latest income,"
                                           "This information is only available for GrantNav data"),
                                           width=1/1)),


                     ),
                     
                     ),
        

        # Navpanel Datagrid 
        ui.nav_panel("Datagrid",
                      ui.layout_columns(
                          ui.card(
                              ui.card_header("Grant overview"),
                              ui.output_data_frame("grid_table")
                          ),
                          ui.card(
                              ui.card_header("Details"),
                              ui.p("Select a row on the left to display details"),
                              ui.accordion(
                                  ui.accordion_panel("Organisation name",
                                                     ui.output_ui("grid_org_name")
                                                  ),
                        
                                  ui.accordion_panel("Grant amount",
                                                     ui.output_ui("grid_amount")),
                                  ui.accordion_panel("Award date",
                                                     ui.output_ui("grid_award_date")),
                                  ui.accordion_panel("Project description",
                                                     ui.output_ui("grid_summary")),
                                  id="grant_details",
                                  open="Organisation name"
                              )
                          ),
                          col_widths=(8,4)
                          
                      ),),

        # Navpanel Map        
        ui.nav_panel("Map", 
                     output_maplibregl("maplibre", height=600)),
        
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


    # Functions for tab "datagrid"

    @render.data_frame
    def grid_table():
        cols = [
            "ID",
            "Title",
            "Type",
            "Subtype"
        ]
        return render.DataGrid(filtered_grants()[cols], 
                                selection_mode="row", 
                                filters=True)

    @render.ui
    def grid_org_name():
        selected = grid_table.data_view(selected=True)
        selected_df = (pd.DataFrame(selected)["ID"]-1)
        name = str(grants.loc[selected_df,"Organisation_name"].sum())
        return ui.p(f"{name}")
    
    @render.ui
    def grid_amount():
        selected = grid_table.data_view(selected=True)
        selected_df = (pd.DataFrame(selected)["ID"]-1)
        amount = str(grants.loc[selected_df,"Amnt_awa"].sum())
        return ui.p(f"{amount} GBP")

    @render.ui
    def grid_grant_date():
        selected = grid_table.data_view(selected=True)
        selected_df = (pd.DataFrame(selected)["ID"]-1)
        awarded = str(grants.loc[selected_df,"Date_awa"].sum())                            
        return ui.p(f"{awarded}")

    @render.ui
    def grid_summary():
        selected = grid_table.data_view(selected=True)
        selected_df = (pd.DataFrame(selected)["ID"]-1)
        return str(grants.loc[selected_df,"Description"].sum())


    # functions for tab "charts"
    @render_widget
    def fig_grants_per_year():
        fig = px.histogram(data_frame=filtered_grants(), y="Year_awa",color="Data_source",
                            labels={
                            "Year_awa": "Year awarded",
                            "Data_source":"Data source"
                            }, 
                            color_discrete_sequence=["#005344","#78c2ad","#DE4712"])
        fig.update_layout(bargap=0.2)
        fig.update_yaxes(dtick=1)
        return fig

    #Function for buildung Maplibre Map
    lc_map = grants[grants['lat'].notna()]
    lc_map["coordinates"] = lc_map[["lon","lat"]].values.tolist()
    
    geojson = df_to_geojson(
        lc_map,
        "coordinates",
        GeometryType.POINT,
        properties=["Title", "Amnt_awa", "Type"],
    )

    lc_circles = Layer(
        type=LayerType.CIRCLE,
        source=GeoJSONSource(data=geojson),
        paint={
            "circle-color": [
                "match",
                ["get", "Type"],
                'Social care',
                '#292f56',
                'Psychological',
                '#21416d',
                'Medical', 
                '#005483',
                'Arts',
                '#006794',
                'Awareness',
                '#007a9a',
                'Advice',
                '#008da1',
                'Communication',
                '#00a1a4',
                'Wellbeing',
                '#00b5a3',
                'Social research',
                '#00ca9a',
                'Core funding',
                '#36dc8d',
                'Rehabilitation',
                '#76ec7e',
                'Epidemiology',
                '#acfa70',
            ],
            "circle_radius": 10,
            "circle-opacity": 0.3,
        },
    )

    map_options = MapOptions(
        style=Carto.POSITRON,
        bounds=BOUNDS,
        fit_bounds_options={"padding": 20},
        hash=True,
    )

    popup_options = PopupOptions(close_button=False)
    def create_map() -> Map:
        m = Map(map_options)
        m.add_control(NavigationControl())
        m.add_layer(lc_circles)
        for _, r in lc_map.iterrows():
            marker = Marker(
                lng_lat=list(r["coordinates"]),
                options=MarkerOptions(color=get_color(r["Type"])),
                popup=Popup(
                    text="Grant type: "+ r["Type"]+ "<br>" +" Title: "+r["Title"] + "<br>" + " Amount awarded (GBP): "+ str(r["Amnt_awa"]),
                    options=popup_options,
                ),
            )
            m.add_marker(marker)
        return m
    
    @render_maplibregl
    def maplibre():
        return create_map()


    # Function building filtered dataframe
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
                                        #"coordinates"
                                        ]])

    @reactive.effect
    @reactive.event(input.reset)
    def _():
        ui.update_slider("grant_amount", value=grant_range)
        ui.update_radio_buttons("lc_dedicated", selected=["Yes","No","Partially"])
        ui.update_selectize("grant_area",selected="AA")
        ui.update_selectize("grant_subtype",selected="All")
        ui.update_radio_buttons("datasource", selected=["Grantnav","NIHR", "UKCDR"])

app = App(app_ui, server)