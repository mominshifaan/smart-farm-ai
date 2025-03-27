# app.py
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# Initialize database with proper error handling
def init_db():
    try:
        conn = sqlite3.connect('farm_data.db')
        c = conn.cursor()
        
        # Farm areas table
        c.execute('''CREATE TABLE IF NOT EXISTS farm_areas
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     name TEXT NOT NULL UNIQUE,
                     size REAL,
                     soil_type TEXT)''')
        
        # Crop cycles table
        c.execute('''CREATE TABLE IF NOT EXISTS crop_cycles
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     area_id INTEGER NOT NULL,
                     crop_type TEXT NOT NULL,
                     start_date DATE NOT NULL,
                     harvest_date DATE,
                     seed_cost REAL DEFAULT 0,
                     fertilizer_cost REAL DEFAULT 0,
                     labor_cost REAL DEFAULT 0,
                     revenue REAL DEFAULT 0,
                     FOREIGN KEY(area_id) REFERENCES farm_areas(id))''')
        
        conn.commit()
    except Exception as e:
        st.error(f"Database error: {str(e)}")
    finally:
        if conn:
            conn.close()

# Main application
def main():
    st.set_page_config(page_title="Farm Manager", layout="wide")
    init_db()
    
    st.title("🌱 Farm Management System")
    
    # Navigation
    page = st.sidebar.selectbox("Menu", ["Dashboard", "Manage Farm Areas", "Add Crop Cycle"])
    
    if page == "Dashboard":
        try:
            conn = sqlite3.connect('farm_data.db')
            df = pd.read_sql('''SELECT 
                                crop_cycles.*, 
                                farm_areas.name as area_name 
                                FROM crop_cycles
                                JOIN farm_areas ON crop_cycles.area_id = farm_areas.id
                                ORDER BY start_date DESC''', conn)
            
            if not df.empty:
                df['profit'] = df['revenue'] - (df['seed_cost'] + df['fertilizer_cost'] + df['labor_cost'])
                st.dataframe(df)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Total Profit", f"${df['profit'].sum():,.2f}")
                with col2:
                    best_crop = df.loc[df['profit'].idxmax()]['crop_type']
                    st.metric("Most Profitable Crop", best_crop)
            else:
                st.info("No crop records found. Add your first crop cycle!")
                
        except Exception as e:
            st.error(f"Error loading data: {str(e)}")
        finally:
            if conn:
                conn.close()
    
    elif page == "Manage Farm Areas":
        with st.form("area_form"):
            st.subheader("Add New Farm Area")
            name = st.text_input("Area Name*")
            size = st.number_input("Size (acres)", min_value=0.1, value=1.0)
            soil = st.selectbox("Soil Type", ["Loam", "Clay", "Sandy", "Other"])
            
            if st.form_submit_button("Save Area"):
                if name:
                    try:
                        conn = sqlite3.connect('farm_data.db')
                        conn.execute("INSERT INTO farm_areas (name, size, soil_type) VALUES (?,?,?)",
                                   (name, size, soil))
                        conn.commit()
                        st.success("Farm area saved!")
                    except sqlite3.IntegrityError:
                        st.error("Area name already exists")
                    except Exception as e:
                        st.error(f"Error saving area: {str(e)}")
                    finally:
                        if conn:
                            conn.close()
                else:
                    st.error("Area name is required")
    
    elif page == "Add Crop Cycle":
        try:
            conn = sqlite3.connect('farm_data.db')
            areas = pd.read_sql("SELECT id, name FROM farm_areas", conn)
            
            if areas.empty:
                st.warning("No farm areas found. Please add a farm area first.")
            else:
                with st.form("crop_form"):
                    st.subheader("Add New Crop Cycle")
                    
                    # Safe area selection
                    area_id = st.selectbox(
                        "Farm Area*",
                        options=areas['id'],
                        format_func=lambda x: areas.loc[areas['id'] == x, 'name'].iloc[0]
                    )
                    
                    crop_type = st.text_input("Crop Type*")
                    start_date = st.date_input("Start Date*", datetime.today())
                    harvest_date = st.date_input("Harvest Date (optional)", None)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        seed_cost = st.number_input("Seed Cost ($)", min_value=0.0, value=0.0)
                        fertilizer_cost = st.number_input("Fertilizer Cost ($)", min_value=0.0, value=0.0)
                    with col2:
                        labor_cost = st.number_input("Labor Cost ($)", min_value=0.0, value=0.0)
                        revenue = st.number_input("Revenue ($)", min_value=0.0, value=0.0)
                    
                    if st.form_submit_button("Save Crop Cycle"):
                        if crop_type and start_date:
                            try:
                                conn.execute('''INSERT INTO crop_cycles 
                                            (area_id, crop_type, start_date, harvest_date,
                                             seed_cost, fertilizer_cost, labor_cost, revenue)
                                            VALUES (?,?,?,?,?,?,?,?)''',
                                          (area_id, crop_type, start_date, harvest_date,
                                           seed_cost, fertilizer_cost, labor_cost, revenue))
                                conn.commit()
                                st.success("Crop cycle saved!")
                            except Exception as e:
                                st.error(f"Error saving crop: {str(e)}")
                        else:
                            st.error("Please fill required fields (*)")
        except Exception as e:
            st.error(f"Error: {str(e)}")
        finally:
            if conn:
                conn.close()

if __name__ == "__main__":
    main()
