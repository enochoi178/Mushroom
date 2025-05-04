import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import io
import numpy as np


#Streamlit UI
st.set_page_config(page_title="LEGO Wishlist Maker", layout="wide")

tab1, tab2, tab3 = st.tabs(["Browse Sets", "Wishlist", "LEGO Insight"])

#Load LEGO set data
@st.cache_data
def load_data():
    df = pd.read_csv("lego_sets_and_themes.csv")
    df = df[df['year_released'].notna() & df['number_of_parts'].notna()]
    df['year_released'] = df['year_released'].astype(float).astype(int)
    df['number_of_parts'] = df['number_of_parts'].astype(float).astype(int)
    return df

df = load_data()

#SQLite setup
conn = sqlite3.connect("wishlist.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS wishlist (
        set_number TEXT PRIMARY KEY,
        set_name TEXT,
        year_released INTEGER,
        number_of_parts INTEGER,
        image_url TEXT,
        theme_name TEXT
    )
''')
conn.commit()

def add_to_wishlist(set_data):
    cursor.execute('''
        INSERT OR IGNORE INTO wishlist (set_number, set_name, year_released, number_of_parts, image_url, theme_name)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        set_data['set_number'],
        set_data['set_name'],
        set_data['year_released'],
        set_data['number_of_parts'],
        set_data['image_url'],
        set_data['theme_name']
    ))
    conn.commit()

def remove_from_wishlist(set_number):
    cursor.execute("DELETE FROM wishlist WHERE set_number=?", (set_number,))
    conn.commit()

def clear_wishlist():
    cursor.execute("DELETE FROM wishlist")
    conn.commit()


with tab1:
    st.title("🧱 LEGO Wishlist Maker")

    #Sidebar Filters
    st.sidebar.header("🔍 Filter LEGO Sets")
    themes = sorted(df['theme_name'].dropna().unique())
    selected_themes = st.sidebar.multiselect("Theme", themes, default=themes[:1])

    year_min, year_max = int(df['year_released'].min()), int(df['year_released'].max())
    year_range = st.sidebar.slider("Year Range", year_min, year_max, (2000, year_max))

    part_min, part_max = int(df['number_of_parts'].min()), int(df['number_of_parts'].max())
    part_range = st.sidebar.slider("Number of Parts", part_min, part_max, (100, 1000))

    search_name = st.sidebar.text_input("Set Name Search", key="set_name_search")

    filtered_df = df.copy()
    if search_name.strip():
        filtered_df = filtered_df[filtered_df['set_name'].str.contains(search_name, case=False, na=False)]
    else:
        if selected_themes:
            filtered_df = filtered_df[filtered_df['theme_name'].isin(selected_themes)]
            filtered_df = filtered_df[
                (filtered_df['year_released'].between(*year_range)) &
                (filtered_df['number_of_parts'].between(*part_range))
            ]
        else:
            filtered_df = filtered_df.iloc[0:0]  # Show nothing if no themes and no search





    #Apply Filters
    filtered_df = df.copy()
    if selected_themes:
        filtered_df = filtered_df[filtered_df['theme_name'].isin(selected_themes)]
        filtered_df = filtered_df[
            (filtered_df['year_released'].between(*year_range)) &
            (filtered_df['number_of_parts'].between(*part_range))
        ]
        if search_name:
            filtered_df = filtered_df[filtered_df['set_name'].str.contains(search_name, case=False, na=False)]
    else:
        filtered_df = filtered_df.iloc[0:0]  # Empty dataframe



    filtered_df = df.copy()
    if search_name.strip():  # If search is not empty, override all filters
        filtered_df = filtered_df[filtered_df['set_name'].str.contains(search_name, case=False, na=False)]
    else:
        if selected_themes:
            filtered_df = filtered_df[filtered_df['theme_name'].isin(selected_themes)]
            filtered_df = filtered_df[
                (filtered_df['year_released'].between(*year_range)) &
                (filtered_df['number_of_parts'].between(*part_range))
            ]
        else:
            filtered_df = filtered_df.iloc[0:0]  # Show nothing if no themes selected


    #Sorting UI (after filter, before display)
    sort_column = st.selectbox(
        "Sort sets by:",
        options=["Set Number", "Number of Parts", "Year Released"],
        index=0,
        key="sort_sets_selectbox"
    )
    sort_order = st.radio("Order", ["Ascending", "Descending"], horizontal=True, key="sort_sets_radio")
    ascending = sort_order == "Ascending"
    sort_col_map = {
        "Set Number": "set_number",
        "Number of Parts": "number_of_parts",
        "Year Released": "year_released"
    }
    col = sort_col_map[sort_column]
    if col in ["number_of_parts", "year_released"]:
        filtered_df[col] = pd.to_numeric(filtered_df[col], errors="coerce")
    filtered_df = filtered_df.sort_values(by=col, ascending=ascending).reset_index(drop=True)

    #Show Filtered & Sorted Sets
    st.subheader("📦 Available LEGO Sets")
    if not selected_themes:
        st.info("Please select at least one theme to view LEGO sets.")
    elif filtered_df.empty:
        st.warning("No sets match your filters.")
    else:
        for _, row in filtered_df.iterrows():
            with st.container():
                cols = st.columns([1, 2])
                with cols[0]:
                    st.image(row['image_url'], width=120)
                with cols[1]:
                    st.markdown(
                        f"**{row['set_name']}** ({int(row['year_released'])})  \n"
                        f"Set #: {row['set_number']}  \n"
                        f"Parts: {int(row['number_of_parts'])}  \n"
                        f"Theme: {row['theme_name']}"
                    )
                    if st.button("Add to Wishlist", key=f"add_{row['set_number']}"):
                        add_to_wishlist(row)
                        st.success(f"{row['set_name']} added to wishlist!", icon="✅")





with tab2:
    st.title("📝 Your Wishlist")

    cursor.execute("SELECT * FROM wishlist")
    wishlist_items = cursor.fetchall()

    PPP = 0.20  # 20 cents per piece

    if wishlist_items:
        wishlist_df = pd.DataFrame(wishlist_items, columns=[
            'set_number', 'set_name', 'year_released', 'number_of_parts', 'image_url', 'theme_name'
        ])
        wishlist_df['number_of_parts'] = pd.to_numeric(wishlist_df['number_of_parts'], errors='coerce').fillna(0)

        #Wishlist Display (list of items first)
        for _, row in wishlist_df.iterrows():
            cols = st.columns([1, 4, 1])
            with cols[0]:
                st.image(row['image_url'], width=100)
            with cols[1]:
                st.markdown(
                    f"**{row['set_name']}** ({int(row['year_released'])}) - {int(row['number_of_parts'])} parts  \n"
                    f"Set #: {row['set_number']}  \nTheme: {row['theme_name']}"
                )
            with cols[2]:
                if st.button("❌ Remove", key=f"remove_{row['set_number']}"):
                    remove_from_wishlist(row['set_number'])
                    st.rerun()

        #CSV Download Button
        csv_buffer = io.StringIO()
        wishlist_df.to_csv(csv_buffer, index=False)
        st.download_button(
            label="📥 Download Wishlist as CSV",
            data=csv_buffer.getvalue(),
            file_name="lego_wishlist.csv",
            mime="text/csv"
        )

        #Clear Wishlist Button
        if st.button("🗑️ Clear Wishlist", key="clear_wishlist"):
            clear_wishlist()
            st.rerun()

        #Estimated Set Price Calculator (after list, before charts)
        st.markdown("---")
        st.subheader("🧮 Estimated Set Price Based Solely on Piece Count")
        wishlist_df['estimated_price'] = wishlist_df['number_of_parts'] * PPP
        total_estimated_price = wishlist_df['estimated_price'].sum()

        st.write(f"**Estimated Price Per Set (at $0.20 per piece):**")
        for _, row in wishlist_df.iterrows():
            st.write(f"- {row['set_name']} ({int(row['number_of_parts'])} parts): **${row['estimated_price']:.2f}**")

        st.metric("Total Estimated Price for Wishlist", f"${total_estimated_price:,.2f}")

        #Total Parts Metric and Visualization (AFTER the calculator)
        st.markdown("---")
        total_parts = int(wishlist_df['number_of_parts'].sum())
        st.metric("Total Number of Parts in Wishlist", f"{total_parts:,}")

        fig = px.bar(
            wishlist_df,
            x="set_name",
            y="number_of_parts",
            title="Number of Parts per Set in Wishlist",
            labels={"set_name": "Set Name", "number_of_parts": "Number of Parts"},
        )
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("No sets in your wishlist yet. Add some using the buttons above!")



with tab3:
    st.header("📊 LEGO Insight")

    #Sets Released Per Year by Theme
    st.subheader("Sets Released Per Year by Theme")
    themes = sorted(df['theme_name'].dropna().unique())
    selected_theme = st.selectbox("Select Theme", themes, key="insight_theme_select")

    # Filter data for the selected theme
    theme_year_df = df[df['theme_name'] == selected_theme]
    sets_per_year = theme_year_df.groupby('year_released').size().reset_index(name='set_count')

    # Ensure all years in range are present, fill missing with 0
    if not sets_per_year.empty:
        all_years = np.arange(df['year_released'].min(), df['year_released'].max() + 1)
        sets_per_year = sets_per_year.set_index('year_released').reindex(all_years, fill_value=0).reset_index()
        sets_per_year.rename(columns={'index': 'year_released'}, inplace=True)

    # Bar chart: Sets released per year for selected theme, with x-axis ticks every 1 year
    fig_theme_year = px.bar(
        sets_per_year,
        x='year_released',
        y='set_count',
        title=f"Number of Sets Released Each Year for '{selected_theme}'",
        labels={'year_released': 'Year Released', 'set_count': 'Number of Sets'}
    )
    fig_theme_year.update_layout(xaxis=dict(tickmode='linear', dtick=1))  # Force x-axis to increment by 1 year
    st.plotly_chart(fig_theme_year, use_container_width=True)

    #Total Sets Released Per Year (All Themes)
    st.subheader("Total Sets Released Per Year (All Themes)")
    sets_per_year_all = df.groupby('year_released').size().reset_index(name='set_count')
    fig_sets_year = px.bar(
        sets_per_year_all,
        x='year_released',
        y='set_count',
        title="Total Sets Released Per Year",
        labels={'year_released': 'Year Released', 'set_count': 'Number of Sets'}
    )
    st.plotly_chart(fig_sets_year, use_container_width=True)

    #Average Number of Parts Per Set By Year
    st.subheader("Average Number of Parts Per Set By Year")
    avg_parts_year = df.groupby('year_released')['number_of_parts'].mean().reset_index()
    fig_avg_parts = px.line(
        avg_parts_year,
        x='year_released',
        y='number_of_parts',
        title="Average Parts Per Set By Year",
        labels={'year_released': 'Year Released', 'number_of_parts': 'Average Number of Parts'}
    )
    st.plotly_chart(fig_avg_parts, use_container_width=True)

    #Top 10 Themes by Number of Sets
    st.subheader("Top 10 Themes by Number of Sets")
    top_themes = df['theme_name'].value_counts().head(10).reset_index()
    top_themes.columns = ['theme_name', 'set_count']
    fig_top_themes = px.bar(
        top_themes,
        x='theme_name',
        y='set_count',
        title="Top 10 Themes by Number of Sets",
        labels={'theme_name': 'Theme', 'set_count': 'Number of Sets'}
    )
    st.plotly_chart(fig_top_themes, use_container_width=True)

    #Distribution of Parts Per Set (Histogram)
    st.subheader("Distribution of Parts Per Set")
    fig_parts_dist = px.histogram(
        df,
        x='number_of_parts',
        nbins=30,
        title="Distribution of Parts Per Set",
        labels={'number_of_parts': 'Number of Parts'}
    )
    st.plotly_chart(fig_parts_dist, use_container_width=True)

# Final DB close
conn.close()
