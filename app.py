import streamlit as st
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from sklearn.ensemble import RandomForestRegressor
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

# AI Prediction Model
def train_prediction_model(df):
    try:
        # Prepare data
        df['duration_days'] = (pd.to_datetime(df['harvest_date']) - pd.to_datetime(df['start_date'])).dt.days
        df['total_cost'] = df[['seed_cost','fertilizer_cost','labor_cost','equipment_cost','other_costs']].sum(axis=1)
        df['profit'] = df['total_revenue'] - df['total_cost']
        
        # Features and target
        X = df[['area_id','crop_type','duration_days','total_cost']]
        X = pd.get_dummies(X, columns=['crop_type'])
        y = df['profit']
        
        # Train model
        model = RandomForestRegressor(n_estimators=100)
        model.fit(X, y)
        return model
    except:
        return None

# Main App
def main():
    st.set_page_config(page_title="Smart Farm AI", layout="wide")
    init_db()
    
    st.title("🌾 AI-Powered Farm Management System")
    st.markdown("""
    <style>
    .big-font { font-size:18px !important; }
    </style>
    """, unsafe_allow_html=True)
    
    # Navigation
    tab1, tab2, tab3, tab4 = st.tabs(["📝 Data Entry", "📊 Dashboard", "🤖 AI Projections", "📂 Database"])
    
    with tab1:
        st.header("Farm Data Entry")
        
        with st.expander("➕ Add New Farm Area", expanded=False):
            with st.form("area_form"):
                area_name = st.text_input("Area Name*")
                size = st.number_input("Size (acres)*", min_value=0.1)
                soil = st.selectbox("Soil Type", ["Loam", "Clay", "Sandy", "Silt", "Other"])
                
                if st.form_submit_button("Save Area"):
                    if area_name:
                        conn = sqlite3.connect('smart_farm.db')
                        try:
                            conn.execute("INSERT INTO farm_areas (area_name, size_acres, soil_type) VALUES (?,?,?)",
                                       (area_name, size, soil))
                            conn.commit()
                            st.success("Farm area saved!")
                        except sqlite3.IntegrityError:
                            st.error("Area name already exists")
                        finally:
                            conn.close()
                    else:
                        st.error("Please enter area name")
        
        with st.expander("🌱 Add Crop Cycle", expanded=True):
            conn = sqlite3.connect('smart_farm.db')
            areas = pd.read_sql("SELECT area_id, area_name FROM farm_areas", conn)
            
            with st.form("crop_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    area = st.selectbox("Farm Area*", 
                                      areas['area_id'], 
                                      format_func=lambda x: areas[areas['area_id']==x]['area_name'].values[0])
                    crop = st.text_input("Crop Type*", help="e.g., Wheat, Corn, Soybeans")
                    start = st.date_input("Start Date*", datetime.today())
                    harvest = st.date_input("Harvest Date")
                with col2:
                    seed = st.number_input("Seed Cost ($)*", min_value=0.0)
                    fertilizer = st.number_input("Fertilizer Cost ($)*", min_value=0.0)
                    labor = st.number_input("Labor Cost ($)*", min_value=0.0)
                
                equip = st.number_input("Equipment Cost ($)", min_value=0.0, value=0.0)
                other = st.number_input("Other Costs ($)", min_value=0.0, value=0.0)
                revenue = st.number_input("Total Revenue ($)*", min_value=0.0)
                notes = st.text_area("Notes")
                
                if st.form_submit_button("Save Crop Cycle"):
                    if crop and start and area:
                        conn.execute("""INSERT INTO crop_cycles 
                                     (area_id, crop_type, start_date, harvest_date,
                                      seed_cost, fertilizer_cost, labor_cost,
                                      equipment_cost, other_costs, total_revenue, notes)
                                     VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                                   (area, crop, start, harvest, seed, fertilizer, 
                                    labor, equip, other, revenue, notes))
                        conn.commit()
                        st.success("Crop cycle saved successfully!")
                    else:
                        st.error("Please fill required fields")
            conn.close()
    
    with tab2:
        st.header("Farm Performance Dashboard")
        conn = sqlite3.connect('smart_farm.db')
        df = pd.read_sql("""SELECT cc.*, fa.area_name, fa.size_acres
                          FROM crop_cycles cc
                          JOIN farm_areas fa ON cc.area_id = fa.area_id""", conn)
        conn.close()
        
        if not df.empty:
            df['total_cost'] = df[['seed_cost','fertilizer_cost','labor_cost','equipment_cost','other_costs']].sum(axis=1)
            df['profit'] = df['total_revenue'] - df['total_cost']
            df['roi'] = (df['profit'] / df['total_cost']) * 100
            df['duration_days'] = (pd.to_datetime(df['harvest_date']) - pd.to_datetime(df['start_date'])).dt.days
            
            # KPIs
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Profit", f"${df['profit'].sum():,.2f}")
            col2.metric("Average ROI", f"{df['roi'].mean():.1f}%")
            best_crop = df.loc[df['profit'].idxmax()]['crop_type']
            col3.metric("Most Profitable Crop", best_crop)
            
            # Visualizations
            st.subheader("Profit Analysis")
            fig1, ax1 = plt.subplots(figsize=(10, 6))
            sns.barplot(data=df, x='crop_type', y='profit', estimator=sum, ax=ax1)
            ax1.set_title("Total Profit by Crop Type")
            st.pyplot(fig1)
            
            st.subheader("Cost Breakdown")
            cost_cols = ['seed_cost','fertilizer_cost','labor_cost','equipment_cost','other_costs']
            cost_df = df[cost_cols].sum().reset_index()
            cost_df.columns = ['Cost Type', 'Amount']
            fig2, ax2 = plt.subplots(figsize=(8, 8))
            ax2.pie(cost_df['Amount'], labels=cost_df['Cost Type'], autopct='%1.1f%%')
            st.pyplot(fig2)
        else:
            st.info("No crop cycle data available. Please add data in the Data Entry tab.")
    
    with tab3:
        st.header("AI Projections")
        conn = sqlite3.connect('smart_farm.db')
        df = pd.read_sql("""SELECT cc.*, fa.area_name 
                          FROM crop_cycles cc
                          JOIN farm_areas fa ON cc.area_id = fa.area_id""", conn)
        conn.close()
        
        if not df.empty and len(df['crop_type'].unique()) > 1:
            model = train_prediction_model(df)
            
            st.subheader("Profit Prediction")
            with st.form("prediction_form"):
                col1, col2 = st.columns(2)
                with col1:
                    pred_area = st.selectbox("Select Farm Area", 
                                           df['area_id'].unique(),
                                           format_func=lambda x: df[df['area_id']==x]['area_name'].values[0])
                    pred_crop = st.selectbox("Select Crop Type", df['crop_type'].unique())
                with col2:
                    pred_duration = st.number_input("Expected Duration (days)", min_value=1, value=90)
                    pred_cost = st.number_input("Estimated Total Cost ($)", min_value=0.0, value=1000.0)
                
                if st.form_submit_button("Predict Profit"):
                    try:
                        # Prepare input for prediction
                        input_data = pd.DataFrame({
                            'area_id': [pred_area],
                            'crop_type': [pred_crop],
                            'duration_days': [pred_duration],
                            'total_cost': [pred_cost]
                        })
                        input_data = pd.get_dummies(input_data, columns=['crop_type'])
                        
                        # Ensure all crop types columns exist
                        for col in df['crop_type'].unique():
                            if f'crop_type_{col}' not in input_data.columns:
                                input_data[f'crop_type_{col}'] = 0
                        
                        # Predict
                        prediction = model.predict(input_data)[0]
                        st.success(f"Predicted Profit: ${prediction:,.2f}")
                        
                        # Show comparison
                        st.subheader("Comparison with Historical Data")
                        crop_data = df[df['crop_type']==pred_crop]
                        if not crop_data.empty:
                            avg_profit = crop_data['profit'].mean()
                            st.metric("Historical Average Profit", f"${avg_profit:,.2f}", 
                                     delta=f"{(prediction-avg_profit):,.2f} vs prediction")
                    except Exception as e:
                        st.error("Prediction failed. Please ensure you have enough historical data.")
            
            st.subheader("Optimal Crop Recommendation")
            if model:
                # Evaluate all crop types
                results = []
                for crop in df['crop_type'].unique():
                    test_case = pd.DataFrame({
                        'area_id': [df['area_id'].mode()[0]],
                        'crop_type': [crop],
                        'duration_days': [df['duration_days'].median()],
                        'total_cost': [df['total_cost'].median()]
                    })
                    test_case = pd.get_dummies(test_case, columns=['crop_type'])
                    for col in df['crop_type'].unique():
                        if f'crop_type_{col}' not in test_case.columns:
                            test_case[f'crop_type_{col}'] = 0
                    results.append({
                        'Crop': crop,
                        'Predicted Profit': model.predict(test_case)[0]
                    })
                
                recommendation = pd.DataFrame(results).sort_values('Predicted Profit', ascending=False)
                st.dataframe(recommendation.style.highlight_max(color='lightgreen'))
            else:
                st.warning("Need more data to generate recommendations")
        else:
            st.warning("Need at least 2 different crop types with historical data for projections")
    
    with tab4:
        st.header("Database Management")
        conn = sqlite3.connect('smart_farm.db')
        
        st.subheader("Farm Areas")
        areas_df = pd.read_sql("SELECT * FROM farm_areas", conn)
        st.dataframe(areas_df)
        
        st.subheader("Crop Cycles")
        crops_df = pd.read_sql("SELECT * FROM crop_cycles", conn)
        st.dataframe(crops_df)
        
        st.subheader("Export Data")
        if st.button("Download Full Data as CSV"):
            full_df = pd.read_sql("""SELECT cc.*, fa.area_name, fa.size_acres, fa.soil_type
                                   FROM crop_cycles cc
                                   JOIN farm_areas fa ON cc.area_id = fa.area_id""", conn)
            st.download_button(
                label="Download",
                data=full_df.to_csv(index=False),
                file_name="farm_data_export.csv",
                mime="text/csv"
            )
        
        conn.close()

if __name__ == "__main__":
    main()
