import streamlit as st
import pandas as pd
import numpy as np
from prophet import Prophet
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(
    page_title="Small Giants - Demand Forecasting", 
    page_icon="🦗", 
    layout="wide"
)

# Custom CSS for Small Giants branding
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #2E8B57, #228B22);
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .main-header h1 {
        color: white;
        margin: 0;
        text-align: center;
    }
    .main-header p {
        color: #E8F5E8;
        margin: 0.5rem 0 0 0;
        text-align: center;
    }
    .metric-card {
        background: #F0F8F0;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #2E8B57;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>🦗 Small Giants - Previsione Domanda & Gestione Inventario</h1>
    <p>Strumento AI per la pianificazione degli stock di proteine alternative sostenibili</p>
</div>
""", unsafe_allow_html=True)

st.write("Carica il tuo file Excel con i dati di vendita per ottenere previsioni della domanda e raccomandazioni per gli ordini!")

# Sidebar for parameters
st.sidebar.header("📊 Parametri di Previsione")
st.sidebar.markdown("*Ottimizza le previsioni per Small Giants*")

forecast_days = st.sidebar.slider("Periodo di Previsione (giorni)", 30, 365, 90, help="Quanto lontano nel futuro prevedere la domanda")
safety_stock_days = st.sidebar.slider("Scorta di Sicurezza (giorni)", 7, 30, 14, help="Giorni extra di inventario come buffer")
lead_time_days = st.sidebar.slider("Tempo di Consegna (giorni)", 1, 30, 7, help="Giorni necessari per ricevere nuovo stock")

# Language toggle
language = st.sidebar.selectbox("Lingua / Language", ["Italiano", "English"])

# Small Giants product suggestions
st.sidebar.markdown("---")
st.sidebar.subheader("🦗 Prodotti Small Giants")
st.sidebar.markdown("""
**Esempi SKU per il file Excel:**
- `CRACKER-ROSMARINO-TIMO`
- `CRACKER-LIME-PEPE`
- `CRACKER-POMODORO-ORIGANO`
- `PUFFS-LIEVITO`
- `TARALLI-CIPOLLA`
- `TARALLI-GRILLO-PEPERONCINO`
- `PASTA-GRILLO-FUSILLI`
- `PASTA-GRILLO-PENNE`
- `FARINA-GRILLO`
- `INSETTI-MIX-BBQ`
- `BARRETTE-CIOCCOLATO`
- `GRATTUGIATO-LIEVITO`
""")

# File uploader
uploaded_file = st.file_uploader(
    "Scegli il tuo file Excel" if language == "Italiano" else "Choose your Excel file", 
    type=['xlsx', 'xls'],
    help="Il file dovrebbe avere le colonne: date, sku, units_sold, on_hand_end"
)

if uploaded_file is not None:
    try:
        # Read the Excel file
        df = pd.read_excel(uploaded_file)
        
        # Display basic info about the data
        st.subheader("📋 Panoramica Dati" if language == "Italiano" else "📋 Data Overview")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Righe Totali" if language == "Italiano" else "Total Rows", len(df))
        with col2:
            st.metric("SKU Unici" if language == "Italiano" else "Unique SKUs", 
                     df['sku'].nunique() if 'sku' in df.columns else 0)
        with col3:
            if 'date' in df.columns:
                date_range = f"{df['date'].dt.date.min()} → {df['date'].dt.date.max()}"
            else:
                date_range = "N/A"
            st.metric("Periodo" if language == "Italiano" else "Date Range", date_range)
        with col4:
            total_units = df['units_sold'].sum() if 'units_sold' in df.columns else 0
            st.metric("Unità Vendute Totali" if language == "Italiano" else "Total Units Sold", 
                     f"{total_units:,.0f}")
        
        # Show first few rows
        st.write("**Prime 5 righe dei tuoi dati:**" if language == "Italiano" else "**First 5 rows of your data:**")
        st.dataframe(df.head())
        
        # Check required columns
        required_columns = ['date', 'sku', 'units_sold', 'on_hand_end']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            st.error(f"❌ Colonne mancanti: {missing_columns}" if language == "Italiano" 
                    else f"❌ Missing required columns: {missing_columns}")
            st.write("**Colonne richieste:** date, sku, units_sold, on_hand_end" if language == "Italiano"
                    else "**Required columns:** date, sku, units_sold, on_hand_end")
        else:
            st.success("✅ Tutte le colonne richieste trovate!" if language == "Italiano" 
                      else "✅ All required columns found!")
            
            # Convert date column to datetime
            try:
                df['date'] = pd.to_datetime(df['date'])
            except Exception as e:
                st.error(f"Errore nel formato data: {str(e)}" if language == "Italiano" 
                        else f"Date format error: {str(e)}")
                st.info("Assicurati che le date siano nel formato YYYY-MM-DD (es. 2024-01-15)" if language == "Italiano"
                       else "Make sure dates are in YYYY-MM-DD format (e.g., 2024-01-15)")
                st.stop()
            
            # SKU selector with Small Giants context
            st.subheader("🦗 Analisi Prodotto Small Giants")
            selected_sku = st.selectbox(
                "Seleziona SKU per analisi dettagliata:" if language == "Italiano" 
                else "Select SKU for detailed analysis:", 
                df['sku'].unique()
            )
            
            # Filter data for selected SKU
            sku_data = df[df['sku'] == selected_sku].copy()
            sku_data = sku_data.sort_values('date')
            
            # Create two columns for charts
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader(f"📈 Storico Vendite - {selected_sku}")
                fig1 = px.line(sku_data, x='date', y='units_sold', 
                              title=f"Vendite Giornaliere per {selected_sku}",
                              color_discrete_sequence=['#2E8B57'])
                fig1.update_layout(
                    height=400,
                    xaxis_title="Data",
                    yaxis_title="Unità Vendute"
                )
                st.plotly_chart(fig1, use_container_width=True)
            
            with col2:
                st.subheader(f"📦 Livelli Inventario - {selected_sku}")
                fig2 = px.line(sku_data, x='date', y='on_hand_end', 
                              title=f"Inventario Fine Giorno per {selected_sku}",
                              color_discrete_sequence=['#FF6B35'])
                fig2.update_layout(
                    height=400,
                    xaxis_title="Data",
                    yaxis_title="Unità in Stock"
                )
                st.plotly_chart(fig2, use_container_width=True)
            
            # Prepare data for Prophet
            if len(sku_data) >= 10:  # Need at least 10 data points for Prophet
                # Aggregate daily sales (in case there are multiple entries per day)
                daily_sales = sku_data.groupby('date')['units_sold'].sum().reset_index()
                daily_sales.columns = ['ds', 'y']  # Prophet requires these column names
                
                st.subheader("🔮 Previsione Domanda AI" if language == "Italiano" else "🔮 AI Demand Forecast")
                
                with st.spinner("Generazione previsione AI... Un momento per favore." if language == "Italiano"
                               else "Generating AI forecast... This may take a moment."):
                    try:
                        # Create and fit Prophet model
                        model = Prophet(
                            daily_seasonality=False,
                            weekly_seasonality=True,
                            yearly_seasonality=True if len(daily_sales) > 365 else False,
                            interval_width=0.95
                        )
                        model.fit(daily_sales)
                        
                        # Make future dataframe
                        future = model.make_future_dataframe(periods=forecast_days)
                        forecast = model.predict(future)
                        
                        # Create forecast visualization
                        fig3 = go.Figure()
                        
                        # Historical data
                        fig3.add_trace(go.Scatter(
                            x=daily_sales['ds'], 
                            y=daily_sales['y'],
                            mode='markers+lines',
                            name='Vendite Storiche' if language == "Italiano" else 'Historical Sales',
                            line=dict(color='#2E8B57', width=3)
                        ))
                        
                        # Forecast line
                        future_dates = forecast[forecast['ds'] > daily_sales['ds'].max()]
                        fig3.add_trace(go.Scatter(
                            x=future_dates['ds'],
                            y=future_dates['yhat'],
                            mode='lines',
                            name='Previsione AI' if language == "Italiano" else 'AI Forecast',
                            line=dict(color='#FF6B35', dash='dash', width=3)
                        ))
                        
                        # Confidence interval
                        fig3.add_trace(go.Scatter(
                            x=future_dates['ds'].tolist() + future_dates['ds'].tolist()[::-1],
                            y=future_dates['yhat_upper'].tolist() + future_dates['yhat_lower'].tolist()[::-1],
                            fill='tonexty',
                            fillcolor='rgba(255,107,53,0.2)',
                            line=dict(color='rgba(255,255,255,0)'),
                            name='Intervallo di Confidenza' if language == "Italiano" else 'Confidence Interval',
                            showlegend=True
                        ))
                        
                        fig3.update_layout(
                            title=f"Previsione Domanda per {selected_sku} - Powered by Small Giants AI",
                            xaxis_title="Data",
                            yaxis_title="Unità Vendute",
                            height=500,
                            template="plotly_white"
                        )
                        st.plotly_chart(fig3, use_container_width=True)
                        
                        # Calculate inventory recommendations
                        st.subheader("📋 Raccomandazioni Inventario" if language == "Italiano" 
                                   else "📋 Inventory Recommendations")
                        
                        # Get current inventory
                        current_inventory = sku_data['on_hand_end'].iloc[-1]
                        
                        # Calculate forecasted demand for lead time + safety stock period
                        total_period = lead_time_days + safety_stock_days
                        period_forecast = future_dates.head(total_period)['yhat'].sum()
                        
                        # Calculate recommended order quantity
                        recommended_order = max(0, period_forecast - current_inventory)
                        
                        # Display recommendations
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Stock Attuale" if language == "Italiano" else "Current Stock", 
                                     f"{current_inventory:,.0f}")
                        with col2:
                            help_text = f"Per i prossimi {total_period} giorni (consegna + sicurezza)" if language == "Italiano" else f"For next {total_period} days (lead time + safety stock)"
                            st.metric("Domanda Prevista" if language == "Italiano" else "Forecasted Demand", 
                                     f"{period_forecast:,.0f}", help=help_text)
                        with col3:
                            st.metric("Ordine Raccomandato" if language == "Italiano" else "Recommended Order", 
                                     f"{recommended_order:,.0f}",
                                     delta=f"{recommended_order - current_inventory:,.0f}")
                        with col4:
                            avg_daily = daily_sales['y'].tail(30).mean() if len(daily_sales) >= 30 else daily_sales['y'].mean()
                            days_of_stock = current_inventory / avg_daily if avg_daily > 0 else float('inf')
                            st.metric("Giorni di Stock" if language == "Italiano" else "Days of Stock", 
                                     f"{days_of_stock:.1f}" if days_of_stock != float('inf') else "∞")
                        
                        # Business insights
                        st.markdown("---")
                        st.subheader("💡 Insight Commerciali" if language == "Italiano" else "💡 Business Insights")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if days_of_stock < safety_stock_days:
                                st.error("🔴 CRITICO: Stock insufficiente!" if language == "Italiano" 
                                        else "🔴 CRITICAL: Insufficient stock!")
                                st.write(f"Rischio stockout in {days_of_stock:.1f} giorni" if language == "Italiano"
                                        else f"Risk of stockout in {days_of_stock:.1f} days")
                            elif days_of_stock < safety_stock_days * 2:
                                st.warning("🟡 ATTENZIONE: Stock basso" if language == "Italiano" 
                                          else "🟡 WARNING: Low stock")
                            else:
                                st.success("🟢 BUONO: Stock sufficiente" if language == "Italiano" 
                                          else "🟢 GOOD: Sufficient stock")
                        
                        with col2:
                            velocity = avg_daily * 7  # Weekly velocity
                            st.info(f"**Velocità settimanale media:** {velocity:.1f} unità" if language == "Italiano"
                                   else f"**Average weekly velocity:** {velocity:.1f} units")
                        
                    except Exception as e:
                        st.error(f"Errore nella generazione della previsione: {str(e)}" if language == "Italiano"
                                else f"Error generating forecast: {str(e)}")
                        st.info("Prova con più dati storici (almeno 2 settimane)" if language == "Italiano"
                               else "Try with more historical data (at least 2 weeks)")
                
                # Summary table for all SKUs
                st.subheader("📊 Riepilogo Tutti i Prodotti Small Giants" if language == "Italiano" 
                           else "📊 Summary for All Small Giants Products")
                
                summary_data = []
                for sku in df['sku'].unique():
                    sku_subset = df[df['sku'] == sku].copy()
                    if len(sku_subset) >= 5:  # Lower threshold for summary
                        # Get basic stats
                        current_stock = sku_subset['on_hand_end'].iloc[-1]
                        avg_daily_sales = sku_subset.groupby('date')['units_sold'].sum().mean()
                        days_stock = current_stock / avg_daily_sales if avg_daily_sales > 0 else float('inf')
                        
                        # Status logic
                        if days_stock < safety_stock_days:
                            status = "🔴 Critico" if language == "Italiano" else "🔴 Critical"
                        elif days_stock < safety_stock_days * 2:
                            status = "🟡 Attenzione" if language == "Italiano" else "🟡 Warning"  
                        else:
                            status = "🟢 Buono" if language == "Italiano" else "🟢 Good"
                        
                        summary_data.append({
                            'SKU': sku,
                            'Stock Attuale' if language == "Italiano" else 'Current Stock': f"{current_stock:,.0f}",
                            'Media Vendite/Giorno' if language == "Italiano" else 'Avg Daily Sales': f"{avg_daily_sales:.1f}",
                            'Giorni di Stock' if language == "Italiano" else 'Days of Stock': f"{days_stock:.1f}" if days_stock != float('inf') else "∞",
                            'Stato' if language == "Italiano" else 'Status': status
                        })
                
                if summary_data:
                    summary_df = pd.DataFrame(summary_data)
                    st.dataframe(summary_df, use_container_width=True)
                else:
                    st.info("Non abbastanza dati per il riepilogo" if language == "Italiano" 
                           else "Not enough data for summary")
                
            else:
                st.warning(f"⚠️ Dati insufficienti per {selected_sku}. Servono almeno 10 punti dati per la previsione." if language == "Italiano"
                          else f"⚠️ Not enough data points for {selected_sku}. Need at least 10 data points for forecasting.")
            
    except Exception as e:
        st.error(f"❌ Errore nella lettura del file: {str(e)}" if language == "Italiano"
                else f"❌ Error reading file: {str(e)}")
        st.write("Assicurati che il file Excel abbia il formato corretto e i nomi delle colonne giusti." if language == "Italiano"
                else "Please make sure your Excel file has the correct format and column names.")

else:
    st.info("👆 Carica un file Excel per iniziare!" if language == "Italiano" 
           else "👆 Please upload an Excel file to get started!")
    
    # Show example data format with Small Giants products
    st.subheader("📋 Formato Dati Atteso" if language == "Italiano" else "📋 Expected Data Format")
    example_data = {
        'date': ['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04'],
        'sku': ['CRACKER-ROSMARINO-TIMO', 'CRACKER-ROSMARINO-TIMO', 'PUFFS-LIEVITO', 'PUFFS-LIEVITO'],
        'units_sold': [15, 12, 25, 30],
        'on_hand_end': [185, 173, 125, 95]
    }
    example_df = pd.DataFrame(example_data)
    st.dataframe(example_df, use_container_width=True)
    
    st.write("**Descrizione colonne:**" if language == "Italiano" else "**Column descriptions:**")
    descriptions = {
        "Italiano": [
            "- **date**: Data della vendita",
            "- **sku**: Codice prodotto Small Giants (es. CRACKER-ROSMARINO-TIMO)",
            "- **units_sold**: Numero di unità vendute in quella data", 
            "- **on_hand_end**: Inventario rimanente a fine giornata"
        ],
        "English": [
            "- **date**: Date of the sales record",
            "- **sku**: Small Giants product code (e.g., CRACKER-ROSMARINO-TIMO)",
            "- **units_sold**: Number of units sold on that date",
            "- **on_hand_end**: Inventory remaining at end of day"
        ]
    }
    
    for desc in descriptions[language]:
        st.write(desc)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 1rem;'>
    <p>🦗 <strong>Small Giants</strong> - Rewriting the rules of food with sustainable alternative proteins</p>
    <p><em>Powered by AI Forecasting Technology</em></p>
</div>
""", unsafe_allow_html=True)
