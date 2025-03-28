import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
import numpy as np

# Initialize database
def init_db():
    conn = sqlite3.connect('smart_farm.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS farm_areas
                 (area_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  area_name TEXT NOT NULL UNIQUE,
                  size_acres REAL,
                  soil_type TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS crop_cycles
                 (cycle_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  area_id INTEGER,
                  crop_type TEXT NOT NULL,
                  start_date DATE NOT NULL,
                  harvest_date DATE,
                  seed_cost REAL DEFAULT 0,
                  fertilizer_cost REAL DEFAULT 0,
                  labor_cost REAL DEFAULT 0,
                  equipment_cost REAL DEFAULT 0,
                  other_costs REAL DEFAULT 0,
                  total_revenue REAL DEFAULT 0,
                  notes TEXT,
                  FOREIGN KEY (area_id) REFERENCES farm_areas(area_id))''')
    conn.commit()
    conn.close()

# AI Model Setup
def prepare_model(df):
    try:
        if df.empty or len(df['crop_type'].unique()) < 2:
            return None
            
        df['duration'] = (pd.to_datetime(df['harvest_date']) - pd.to_datetime(df['start_date'])).dt.days
        df['total_cost'] = df[['seed_cost','fertilizer_cost','labor_cost','equipment_cost','other_costs']].sum(axis=1)
        df['profit'] = df['total_revenue'] - df['total_cost']
        
        # Create pipeline with proper feature encoding
        preprocessor = ColumnTransformer(
            transformers=[
                ('cat', OneHotEncoder(handle_unknown='ignore'), ['crop_type'])
            ],
            remainder='passthrough'
        )
        
        model = Pipeline([
            ('preprocessor', preprocessor),
            ('regressor', RandomForestRegressor(n_estimators=50, random_state=42))
        ])
        
        X = df[['area_id', 'crop_type', 'duration', 'total_cost']]
        y = df['profit']
        
        model.fit(X, y)
        return model
        
    except Exception as e:
        st.error(f"Model preparation failed: {str(e)}")
        return None

# Main App
def main():
    st.set_page_config(page_title="Smart Farm Manager", layout="wide")
    init_db()
    
    st.title("🌱 AI-Powered Farm Management System")
    
    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📥 Data Input", "📊 Visualization", "🤖 AI Predictions", "💾 Database"])
    
    with tab1:
        st.header("Farm Data Input")
        conn = sqlite3.connect('smart_farm.db')
        
        # Farm Area Input
        with st.expander("Add/Edit Farm Areas"):
            with st.form("area_form"):
                col1, col2 = st.columns(2)
                with col1:
                    area_name = st.text_input("Area Name*")
                    size = st.number_input("Size (acres)*", min_value=0.1)
                with col2:
                    soil = st.selectbox("Soil Type*", ["Loam", "Clay", "Sandy", "Silt", "Other"])
                
                if st.form_submit_button("Save Area"):
                    if area_name and size:
                        try:
                            conn.execute("INSERT INTO farm_areas (area_name, size_acres, soil_type) VALUES (?,?,?)",
                                       (area_name, size, soil))
                            conn.commit()
                            st.success("Area saved!")
                        except sqlite3.IntegrityError:
                            st.error("Area name already exists")
                    else:
                        st.error("Please fill required fields")
        
        # Crop Cycle Input
        with st.expander("Add Crop Cycle"):
            areas = pd.read_sql("SELECT area_id, area_name FROM farm_areas", conn)
            
            if not areas.empty:
                with st.form("crop_form"):
                    col1, col2 = st.columns(2)
                    with col1:
                        area = st.selectbox("Farm Area*", 
                                          areas['area_id'], 
                                          format_func=lambda x: areas[areas['area_id']==x]['area_name'].values[0])
                        crop = st.text_input("Crop Type*")
                        start = st.date_input("Start Date*", datetime.today())
                        harvest = st.date_input("Harvest Date")
                    with col2:
                        seed = st.number_input("Seed Cost ($)*", min_value=0.0)
                        fertilizer = st.number_input("Fertilizer Cost ($)*", min_value=0.0)
                        labor = st.number_input("Labor Cost ($)*", min_value=0.0)
                    
                    equip = st.number_input("Equipment Cost ($)", min_value=0.0, value=0.0)
                    other = st.number_input("Other Costs ($)", min_value=0.0, value=0.0)
                    revenue = st.number_input("Revenue ($)*", min_value=0.0)
                    notes = st.text_area("Notes")
                    
                    if st.form_submit_button("Save Crop"):
                        if crop and start and area:
                            conn.execute("""INSERT INTO crop_cycles 
                                         (area_id, crop_type, start_date, harvest_date,
                                          seed_cost, fertilizer_cost, labor_cost,
                                          equipment_cost, other_costs, total_revenue, notes)
                                         VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                                       (area, crop, start, harvest, seed, fertilizer, 
                                        labor, equip, other, revenue, notes))
                            conn.commit()
                            st.success("Crop cycle saved!")
                        else:
                            st.error("Please fill required fields")
            else:
                st.warning("No farm areas found. Please add areas first.")
        conn.close()
    
    with tab2:
        st.header("Data Visualization")
        conn = sqlite3.connect('smart_farm.db')
        df = pd.read_sql("""SELECT cc.*, fa.area_name, fa.soil_type
                          FROM crop_cycles cc
                          JOIN farm_areas fa ON cc.area_id = fa.area_id""", conn)
        conn.close()
        
        if not df.empty:
            df['total_cost'] = df[['seed_cost','fertilizer_cost','labor_cost','equipment_cost','other_costs']].sum(axis=1)
            df['profit'] = df['total_revenue'] - df['total_cost']
            df['date'] = pd.to_datetime(df['start_date'])
            
            st.subheader("Profit Over Time")
            fig1, ax1 = plt.subplots(figsize=(10, 4))
            df.groupby('date')['profit'].sum().plot(ax=ax1, marker='o')
            ax1.set_title("Cumulative Profit Over Time")
            ax1.grid(True)
            st.pyplot(fig1)
            
            st.subheader("Cost Breakdown")
            cost_cols = ['seed_cost','fertilizer_cost','labor_cost','equipment_cost','other_costs']
            cost_df = df[cost_cols].sum().reset_index()
            cost_df.columns = ['Cost Type', 'Amount']
            fig2, ax2 = plt.subplots(figsize=(8, 8))
            ax2.pie(cost_df['Amount'], labels=cost_df['Cost Type'], autopct='%1.1f%%')
            st.pyplot(fig2)
        else:
            st.info("No data available. Please add farm data in the Input tab.")
    
    with tab3:
        st.header("AI Predictions")
        conn = sqlite3.connect('smart_farm.db')
        df = pd.read_sql("""SELECT cc.*, fa.area_name
                          FROM crop_cycles cc
                          JOIN farm_areas fa ON cc.area_id = fa.area_id""", conn)
        conn.close()
        
        model = prepare_model(df)
        
        if model:
            with st.expander("Profit Prediction"):
                with st.form("prediction_form"):
                    col1, col2 = st.columns(2)
                    with col1:
                        pred_area = st.selectbox("Farm Area", 
                                               df['area_id'].unique(),
                                               format_func=lambda x: df[df['area_id']==x]['area_name'].values[0])
                        pred_crop = st.selectbox("Crop Type", df['crop_type'].unique())
                    with col2:
                        pred_duration = st.number_input("Duration (days)", min_value=1, value=90)
                        pred_cost = st.number_input("Total Cost ($)", min_value=0.0, value=1000.0)
                    
                    if st.form_submit_button("Predict Profit"):
                        try:
                            input_data = pd.DataFrame({
                                'area_id': [pred_area],
                                'crop_type': [pred_crop],
                                'duration': [pred_duration],
                                'total_cost': [pred_cost]
                            })
                            
                            prediction = model.predict(input_data)[0]
                            st.success(f"Predicted Profit: ${prediction:,.2f}")
                        except Exception as e:
                            st.error(f"Prediction failed: {str(e)}")
            
            with st.expander("Optimal Crop Recommendation"):
                try:
                    results = []
                    for crop in df['crop_type'].unique():
                        test_case = pd.DataFrame({
                            'area_id': [df['area_id'].mode()[0]],
                            'crop_type': [crop],
                            'duration': [df['duration'].median()],
                            'total_cost': [df['total_cost'].median()]
                        })
                        results.append({
                            'Crop': crop,
                            'Predicted Profit': model.predict(test_case)[0]
                        })
                    
                    recommendation = pd.DataFrame(results).sort_values('Predicted Profit', ascending=False)
                    st.dataframe(recommendation.style.highlight_max(color='lightgreen'))
                except Exception as e:
                    st.error(f"Recommendation failed: {str(e)}")
        else:
            st.warning("Need at least 2 crop types with historical data for predictions")
    
    with tab4:
        st.header("Database View")
        conn = sqlite3.connect('smart_farm.db')
        
        st.subheader("Farm Areas")
        areas_df = pd.read_sql("SELECT * FROM farm_areas", conn)
        st.dataframe(areas_df)
        
        st.subheader("Crop Cycles")
        crops_df = pd.read_sql("SELECT * FROM crop_cycles", conn)
        st.dataframe(crops_df)
        
        st.download_button(
            "Export Full Data",
            pd.read_sql("""SELECT cc.*, fa.area_name, fa.size_acres, fa.soil_type
                         FROM crop_cycles cc
                         JOIN farm_areas fa ON cc.area_id = fa.area_id""", conn).to_csv(index=False),
            "farm_data.csv",
            "text/csv"
        )
        conn.close()

if __name__ == "__main__":
    main()
