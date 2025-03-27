import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

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

def get_areas_df(conn):
    """Safely get areas DataFrame with validation"""
    areas_df = pd.read_sql("SELECT area_id, area_name FROM farm_areas", conn)
    if areas_df.empty:
        st.warning("No farm areas found. Please add areas first.")
        return None
    return areas_df

def main():
    st.set_page_config(page_title="Smart Farm AI", layout="wide")
    init_db()
    
    st.title("🌾 Farm Management System (Editable)")
    
    # Navigation
    tab1, tab2, tab3 = st.tabs(["🏡 Farm Areas", "🌱 Crop Cycles", "📊 Dashboard"])
    
    with tab1:
        st.header("Manage Farm Areas")
        conn = sqlite3.connect('smart_farm.db')
        
        # Add new area
        with st.expander("➕ Add New Area", expanded=False):
            with st.form("add_area_form"):
                new_name = st.text_input("Area Name*")
                new_size = st.number_input("Size (acres)*", min_value=0.1)
                new_soil = st.selectbox("Soil Type*", ["Loam", "Clay", "Sandy", "Silt", "Other"])
                
                if st.form_submit_button("Add Area"):
                    if new_name and new_size:
                        try:
                            conn.execute("INSERT INTO farm_areas (area_name, size_acres, soil_type) VALUES (?,?,?)",
                                       (new_name, new_size, new_soil))
                            conn.commit()
                            st.success("Area added successfully!")
                        except sqlite3.IntegrityError:
                            st.error("Area name already exists")
                    else:
                        st.error("Please fill required fields")
        
        # Edit existing areas
        st.subheader("Edit Existing Areas")
        areas_df = pd.read_sql("SELECT * FROM farm_areas ORDER BY area_name", conn)
        
        if not areas_df.empty:
            for _, row in areas_df.iterrows():
                with st.expander(f"🖊️ {row['area_name']}", expanded=False):
                    with st.form(f"edit_area_{row['area_id']}"):
                        edit_name = st.text_input("Area Name", value=row['area_name'], key=f"name_{row['area_id']}")
                        edit_size = st.number_input("Size (acres)", value=row['size_acres'], key=f"size_{row['area_id']}")
                        edit_soil = st.selectbox("Soil Type", ["Loam", "Clay", "Sandy", "Silt", "Other"], 
                                               index=["Loam", "Clay", "Sandy", "Silt", "Other"].index(row['soil_type']), 
                                               key=f"soil_{row['area_id']}")
                        
                        if st.form_submit_button("Save Changes"):
                            try:
                                conn.execute("""UPDATE farm_areas 
                                              SET area_name = ?, size_acres = ?, soil_type = ?
                                              WHERE area_id = ?""",
                                           (edit_name, edit_size, edit_soil, row['area_id']))
                                conn.commit()
                                st.success("Changes saved!")
                                st.rerun()
                            except sqlite3.IntegrityError:
                                st.error("Area name already exists")
                        
                        if st.form_submit_button("❌ Delete Area"):
                            conn.execute("DELETE FROM farm_areas WHERE area_id = ?", (row['area_id'],))
                            conn.commit()
                            st.warning("Area deleted!")
                            st.rerun()
        else:
            st.info("No farm areas found. Add your first area above.")
        
        conn.close()
    
    with tab2:
        st.header("Manage Crop Cycles")
        conn = sqlite3.connect('smart_farm.db')
        
        # Add new crop cycle
        with st.expander("🌱 Add New Crop Cycle", expanded=True):
            areas_df = get_areas_df(conn)
            
            if areas_df is not None:
                with st.form("add_crop_form", clear_on_submit=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        area_id = st.selectbox("Farm Area*", 
                                             areas_df['area_id'], 
                                             format_func=lambda x: areas_df[areas_df['area_id']==x]['area_name'].values[0])
                        crop_type = st.text_input("Crop Type*")
                        start_date = st.date_input("Start Date*", datetime.today())
                        harvest_date = st.date_input("Harvest Date")
                    with col2:
                        seed_cost = st.number_input("Seed Cost ($)*", min_value=0.0)
                        fertilizer_cost = st.number_input("Fertilizer Cost ($)*", min_value=0.0)
                        labor_cost = st.number_input("Labor Cost ($)*", min_value=0.0)
                    
                    equipment_cost = st.number_input("Equipment Cost ($)", min_value=0.0, value=0.0)
                    other_costs = st.number_input("Other Costs ($)", min_value=0.0, value=0.0)
                    total_revenue = st.number_input("Total Revenue ($)*", min_value=0.0)
                    notes = st.text_area("Notes")
                    
                    if st.form_submit_button("Add Crop Cycle"):
                        if crop_type and start_date and area_id:
                            conn.execute("""INSERT INTO crop_cycles 
                                         (area_id, crop_type, start_date, harvest_date,
                                          seed_cost, fertilizer_cost, labor_cost,
                                          equipment_cost, other_costs, total_revenue, notes)
                                         VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                                       (area_id, crop_type, start_date, harvest_date, 
                                        seed_cost, fertilizer_cost, labor_cost,
                                        equipment_cost, other_costs, total_revenue, notes))
                            conn.commit()
                            st.success("Crop cycle added successfully!")
                        else:
                            st.error("Please fill required fields")
        
        # Edit existing crop cycles
        st.subheader("Edit Existing Crop Cycles")
        crops_df = pd.read_sql("""SELECT cc.*, fa.area_name 
                                FROM crop_cycles cc
                                JOIN farm_areas fa ON cc.area_id = fa.area_id
                                ORDER BY start_date DESC""", conn)
        
        if not crops_df.empty:
            for _, row in crops_df.iterrows():
                with st.expander(f"🖊️ {row['crop_type']} ({row['area_name']})", expanded=False):
                    with st.form(f"edit_crop_{row['cycle_id']}"):
                        # Get current areas for dropdown
                        areas_df = get_areas_df(conn)
                        
                        if areas_df is not None:
                            col1, col2 = st.columns(2)
                            with col1:
                                current_area_index = areas_df[areas_df['area_id']==row['area_id']].index
                                if not current_area_index.empty:
                                    edit_area = st.selectbox("Farm Area", 
                                                           areas_df['area_id'], 
                                                           index=current_area_index[0],
                                                           key=f"area_{row['cycle_id']}")
                                else:
                                    st.warning("Original farm area no longer exists")
                                    edit_area = st.selectbox("Farm Area", 
                                                           areas_df['area_id'], 
                                                           key=f"area_{row['cycle_id']}")
                                
                                edit_crop = st.text_input("Crop Type", value=row['crop_type'], key=f"crop_{row['cycle_id']}")
                                edit_start = st.date_input("Start Date", 
                                                          value=datetime.strptime(row['start_date'], '%Y-%m-%d'), 
                                                          key=f"start_{row['cycle_id']}")
                                edit_harvest = st.date_input("Harvest Date", 
                                                             value=datetime.strptime(row['harvest_date'], '%Y-%m-%d') if row['harvest_date'] else None,
                                                             key=f"harvest_{row['cycle_id']}")
                            with col2:
                                edit_seed = st.number_input("Seed Cost ($)", value=row['seed_cost'], key=f"seed_{row['cycle_id']}")
                                edit_fert = st.number_input("Fertilizer Cost ($)", value=row['fertilizer_cost'], key=f"fert_{row['cycle_id']}")
                                edit_labor = st.number_input("Labor Cost ($)", value=row['labor_cost'], key=f"labor_{row['cycle_id']}")
                            
                            edit_equip = st.number_input("Equipment Cost ($)", value=row['equipment_cost'], key=f"equip_{row['cycle_id']}")
                            edit_other = st.number_input("Other Costs ($)", value=row['other_costs'], key=f"other_{row['cycle_id']}")
                            edit_revenue = st.number_input("Revenue ($)", value=row['total_revenue'], key=f"revenue_{row['cycle_id']}")
                            edit_notes = st.text_area("Notes", value=row['notes'], key=f"notes_{row['cycle_id']}")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.form_submit_button("💾 Save Changes"):
                                    conn.execute("""UPDATE crop_cycles 
                                                SET area_id = ?, crop_type = ?, start_date = ?, harvest_date = ?,
                                                    seed_cost = ?, fertilizer_cost = ?, labor_cost = ?,
                                                    equipment_cost = ?, other_costs = ?, total_revenue = ?, notes = ?
                                                WHERE cycle_id = ?""",
                                               (edit_area, edit_crop, edit_start, edit_harvest,
                                                edit_seed, edit_fert, edit_labor, edit_equip,
                                                edit_other, edit_revenue, edit_notes, row['cycle_id']))
                                    conn.commit()
                                    st.success("Changes saved!")
                                    st.rerun()
                            with col2:
                                if st.form_submit_button("❌ Delete Record"):
                                    conn.execute("DELETE FROM crop_cycles WHERE cycle_id = ?", (row['cycle_id'],))
                                    conn.commit()
                                    st.warning("Record deleted!")
                                    st.rerun()
        else:
            st.info("No crop cycles found. Add your first crop cycle above.")
        
        conn.close()
    
    with tab3:
        st.header("Farm Dashboard")
        conn = sqlite3.connect('smart_farm.db')
        df = pd.read_sql("""SELECT cc.*, fa.area_name, fa.soil_type
                          FROM crop_cycles cc
                          JOIN farm_areas fa ON cc.area_id = fa.area_id""", conn)
        conn.close()
        
        if not df.empty:
            df['total_cost'] = df[['seed_cost','fertilizer_cost','labor_cost','equipment_cost','other_costs']].sum(axis=1)
            df['profit'] = df['total_revenue'] - df['total_cost']
            df['roi'] = (df['profit'] / df['total_cost']) * 100
            
            # KPIs
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Profit", f"${df['profit'].sum():,.2f}")
            col2.metric("Average ROI", f"{df['roi'].mean():.1f}%")
            best_crop = df.loc[df['profit'].idxmax()]['crop_type']
            col3.metric("Most Profitable Crop", best_crop)
            
            # Visualizations
            st.subheader("Profit by Crop Type")
            st.bar_chart(df.groupby('crop_type')['profit'].sum())
            
            st.subheader("Profit by Soil Type")
            st.bar_chart(df.groupby('soil_type')['profit'].mean())
        else:
            st.info("No data available. Please add farm areas and crop cycles.")

if __name__ == "__main__":
    main()
