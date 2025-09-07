import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from datetime import time

# --- Stílusbeállítások a látványosabb diagramokhoz (sötét téma) ---
plt.style.use('dark_background')
plt.rcParams['figure.facecolor'] = '#0E1117' # Streamlit sötét háttérszín
plt.rcParams['axes.facecolor'] = '#0E1117'

# --- Az adatelemző funkciók (változatlanok) ---

def load_and_prepare_data(uploaded_file):
    """Betölti a feltöltött fájlt és előkészíti az adatokat."""
    try:
        df = pd.read_csv(uploaded_file)
        df.rename(columns={
            "Kód": "symbol", "Nyitási irány": "direction", "Zárási idő (UTC+0)": "close_time",
            "Nettó €": "net_profit", "Egyenleg €": "balance", "Záró mennyiség": "lots"
        }, inplace=True)

        df['close_time'] = pd.to_datetime(df['close_time'], format='%d/%m/%Y %H:%M:%S.%f')
        for col in ['net_profit', 'balance']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df['lots'] = df['lots'].str.extract(r'(\d+\.\d+)').astype(float)
        df['profitable'] = df['net_profit'] > 0
        return df
    except Exception as e:
        st.error(f"Hiba történt a fájl feldolgozása közben: {e}")
        return None

def calculate_key_stats(df):
    """Kiszámolja és visszaadja a főbb statisztikai mutatókat egy szótárban."""
    total_trades = len(df)
    winning_trades = df[df['profitable'] == True]
    losing_trades = df[df['profitable'] == False]
    
    win_rate = (len(winning_trades) / total_trades) * 100 if total_trades > 0 else 0
    total_profit = df['net_profit'].sum()
    
    total_gains = winning_trades['net_profit'].sum()
    total_losses = abs(losing_trades['net_profit'].sum())
    
    avg_win = winning_trades['net_profit'].mean() if len(winning_trades) > 0 else 0
    avg_loss = losing_trades['net_profit'].mean() if len(losing_trades) > 0 else 0
    
    profit_factor = total_gains / total_losses if total_losses > 0 else float('inf')
    expectancy = (win_rate/100 * avg_win) + ((100-win_rate)/100 * avg_loss)

    return {
        "Összes trade": total_trades,
        "Nyerési arány": f"{win_rate:.2f}%",
        "Teljes nettó profit": f"{total_profit:.2f} €",
        "Profit Faktor": f"{profit_factor:.2f}",
        "Várható érték/trade": f"{expectancy:.2f} €",
        "Átlagos nyerő trade": f"{avg_win:.2f} €",
        "Átlagos vesztő trade": f"{avg_loss:.2f} €",
    }

# --- A STREAMLIT ALKALMAZÁS FELÉPÍTÉSE ---

# Oldal konfigurációja (cím, ikon)
st.set_page_config(layout="wide", page_title="Trading Napló Analízis")

# Főcím
st.title('📊 Trading Napló Analízis')

# Oldalsáv (Sidebar) a fájlfeltöltéshez
with st.sidebar:
    st.header("Beállítások")
    uploaded_file = st.file_uploader("Töltsd fel a CSV riportodat", type=["csv"])

# Fő tartalom
if uploaded_file is None:
    st.info("Kérlek, tölts fel egy CSV fájlt az elemzés megkezdéséhez az oldalsávon.")
else:
    # Adatok betöltése és feldolgozása
    trading_data = load_and_prepare_data(uploaded_file)
    
    if trading_data is not None:
        # Fő statisztikák megjelenítése metrikákkal
        stats = calculate_key_stats(trading_data)
        st.header("Főbb Kereskedési Statisztikák")
        cols = st.columns(4)
        cols[0].metric("Teljes Nettó Profit", stats["Teljes nettó profit"])
        cols[1].metric("Nyerési Arány", stats["Nyerési arány"])
        cols[2].metric("Profit Faktor", stats["Profit Faktor"])
        cols[3].metric("Összes Trade", stats["Összes trade"])

        # Fülek létrehozása a különböző elemzéseknek
        tab1, tab2, tab3, tab4 = st.tabs(["📈 Egyenleg Görbe", "🏛️ Instrumentumok", "⚖️ Buy vs. Sell", "📅 Hét Napjai"])

        with tab1:
            st.subheader("Egyenleg alakulása az idő függvényében")
            fig, ax = plt.subplots(figsize=(7, 3)) # MÉRET MÓDOSÍTVA
            ax.plot(trading_data['close_time'], trading_data['balance'], color='#FF5733', label='Egyenleg (€)')
            ax.fill_between(trading_data['close_time'], trading_data['balance'], alpha=0.3, color='#FF5733')
            ax.set_title('Egyenleg alakulása')
            ax.set_xlabel('Dátum')
            ax.set_ylabel('Egyenleg (€)')
            ax.grid(True, linestyle='--', alpha=0.3)
            ax.legend()
            st.pyplot(fig)

        with tab2:
            st.subheader("Teljesítmény instrumentumonként")
            symbol_performance = trading_data.groupby('symbol').agg(
                total_profit=('net_profit', 'sum'),
                trade_count=('symbol', 'count'),
                win_rate=('profitable', lambda x: x.mean() * 100)
            ).round(2).sort_values('total_profit', ascending=True)
            
            st.dataframe(symbol_performance)
            
            fig, ax = plt.subplots(figsize=(7, 3)) # MÉRET MÓDOSÍTVA
            colors = ['#2ECC71' if x > 0 else '#E74C3C' for x in symbol_performance['total_profit']]
            sns.barplot(x=symbol_performance['total_profit'], y=symbol_performance.index, palette=colors, ax=ax, orient='h')
            ax.set_title('Nettó Profit Instrumentumonként (€)')
            ax.set_xlabel('Nettó Profit (€)')
            ax.set_ylabel('Instrumentum')
            st.pyplot(fig)

        with tab3:
            st.subheader("Buy vs. Sell pozíciók összehasonlítása")
            performance = trading_data.groupby('direction')['profitable'].value_counts(normalize=True).unstack().fillna(0)
            performance = (performance * 100).round(2)
            performance.rename(columns={True: 'Nyerő (%)', False: 'Vesztő (%)'}, inplace=True)
            
            st.dataframe(performance)

            fig, ax = plt.subplots()
            performance.plot(kind='bar', stacked=True, color=['#E74C3C', '#2ECC71'], ax=ax, figsize=(5, 3)) # MÉRET MÓDOSÍTVA
            ax.set_title('Buy vs. Sell: Nyerő/Vesztő arány')
            ax.set_ylabel('Százalékos arány (%)')
            ax.set_xlabel('Pozíció iránya')
            ax.tick_params(axis='x', rotation=0)
            st.pyplot(fig)

        with tab4:
            st.subheader("Teljesítmény a hét napjai szerint")
            trading_data['day_of_week'] = trading_data['close_time'].dt.day_name()
            days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            day_performance = trading_data.groupby('day_of_week').agg(
                total_profit=('net_profit', 'sum'),
                trade_count=('symbol', 'count'),
                win_rate=('profitable', lambda x: x.mean() * 100)
            ).reindex(days_order).dropna().round(2)
            
            st.dataframe(day_performance)

            fig, ax = plt.subplots(figsize=(7, 3)) # MÉRET MÓDOSÍTVA
            colors = ['#2ECC71' if x > 0 else '#E74C3C' for x in day_performance['total_profit']]
            sns.barplot(x=day_performance.index, y=day_performance['total_profit'], palette=colors, ax=ax)
            ax.set_title('Nettó Profit a Hét Napjai Szerint (€)')
            ax.set_ylabel('Nettó Profit (€)')
            ax.set_xlabel('Nap')
            st.pyplot(fig)