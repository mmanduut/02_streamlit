import streamlit as st
import pandas as pd
import io

st.title("Summary E-Commerce Transaction Processor")

# Input for withdrawal amount and date
withdraw_date = st.date_input("Input tanggal penarikan (withdrawal date)")

uploaded_file = st.file_uploader("Upload your file", type=["csv", "xlsx"])

if uploaded_file:
    run = st.button("Run Processing")
    if run:
        # Read file
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, sep=";")
        else:
            df = pd.read_excel(uploaded_file)

        # Replace all commas with dots in the entire DataFrame
        df = df.map(lambda x: str(x).replace(',', '.') if isinstance(x, str) else x)

        # PRODUCT
        df['PRODUCT'] = df['PRODUCT'].astype(str).str.replace('.0', '', regex=False).str.zfill(5)

        # SHIPPING_FEE
        df['SHIPPING_FEE'] = df['SHIPPING_FEE'].astype(str).str.replace(',', '.')
        df['SHIPPING_FEE'] = pd.to_numeric(df['SHIPPING_FEE'], errors='coerce').astype('float64')

        # Convert columns 6 to 20 (index 5 to 19) to numeric
        for col in df.columns[3:20]:
            df[col] = pd.to_numeric(df[col], errors='coerce').round(2).astype('float64')
        # add new column SALES
        df['SALES'] = df['QUANTITY'] * df['PRICE']
        cols = list(df.columns)
        temp_col = cols.pop(-1)
        cols.insert(5, temp_col)
        df = df[cols]

        # add new column INVOICE
        df['INVOICE'] = df['SALES'] + df['TOTAL_DISCOUNT']
        cols = list(df.columns)
        temp_col = cols.pop(-1)
        cols.insert(0, temp_col)
        df = df[cols]

        # add new column DATE
        date = "01/10/2025"
        date = pd.to_datetime(date, format='%d/%m/%Y')
        df['DATE'] = date
        cols = list(df.columns)
        temp_col = cols.pop(-1)
        cols.insert(0, temp_col)
        df = df[cols]

        # Map warehouse values
        warehouse_map = {
            "DC ECOMMERCE TEGAL": "DCTE",
            "DC ECOMMERCE PALEMBANG": "DCPA",
            "DC ECOMMERCE MEDAN": "DCME",
            "DC ECOMMERCE MAKASSAR": "DCMA",
            "DC ECOMMERCE JAKARTA 1": "DCJA",
            "DC ECOMMERCE KEDIRI": "DCKE"
        }
        df["CODE"] = df["WAREHOUSE_NAME"].map(warehouse_map)

        # generate invoice number
        df['INVOICE_ID'] = "INV_SP" + df['DATE'].dt.strftime('%d%m%y') + df['CODE']
        cols = list(df.columns)
        temp_col = cols.pop(-1)
        cols.insert(1, temp_col)
        df = df[cols]
        df.drop(columns=["CODE"], axis=1, inplace=True)

        # generate settlement ID
        df['SETTLEMENT_ID'] = "SE_SP" + df['DATE'].dt.strftime('%d%m%y')
        cols = list(df.columns)
        temp_col = cols.pop(-1)
        cols.insert(1, temp_col)
        df = df[cols]

        # generate PRODUCT_ID
        df['PRODUCT_ID'] = df['INVOICE_ID'] + "_" + df['PRODUCT']

        sum = df.groupby("INVOICE_ID")[['SALES', 'INVOICE', 'TOTAL_DISCOUNT', 'SHIPPING_FEE',
                                        'AFFILIATE_COMMISSION_FEE', 'TOTAL_COMISSION_PROCESSING_AND_SERVICE_FEE',
                                        'CALCULATED_PAYOUT_AMOUNT']].sum().reset_index()

        summary_map = {
            "AFFILIATE_COMMISSION_FEE": "MARKETING_FEE",
            "TOTAL_COMISSION_PROCESSING_AND_SERVICE_FEE": "ADMIN_FEE",
            "CALCULATED_PAYOUT_AMOUNT": "ESCROW_AMOUNT",
        }

        sum.rename(columns=summary_map, inplace=True)
        sum['DATE'] = df['DATE']
        sum['SETTLEMENT_ID'] = df['SETTLEMENT_ID']
        cols = list(sum.columns)
        cols.remove('DATE')
        cols.remove('INVOICE_ID')
        cols.remove('SETTLEMENT_ID')
        sum = sum[['SETTLEMENT_ID', 'DATE', 'INVOICE_ID'] + cols]

         # Add a total row to sum for all integer/float columns
        total_row = {col: sum[col].sum() if pd.api.types.is_numeric_dtype(sum[col]) else '' for col in sum.columns}
        total_row['SETTLEMENT_ID'] = 'TOTAL'
        total_row['DATE'] = ''
        total_row['INVOICE_ID'] = ''
        sum = pd.concat([sum, pd.DataFrame([total_row])], ignore_index=True)
        
        # st.markdown(f"### Summary of Settlement on {withdraw_date}")
        st.dataframe(sum)

        # Escrow Balance Calculation Table
        initial_balance = 852_855_295  # jumlah saldo saat penarikan

        # Get total escrow amount from the TOTAL row in summary
        # total_escrow_amount = sum.loc[sum['SETTLEMENT_ID'] == 'TOTAL', 'ESCROW_AMOUNT']#.values[0]
        # escrow_amount = withdraw_amount if withdraw_amount > 0 else total_escrow_amount
        # remaining_balance = initial_balance - escrow_amount

        # escrow_balance_table = pd.DataFrame({
        #     'Keterangan': ['Jumlah saldo saat penarikan', 'Total Escrow Amount', 'Nominal dana ditarik', 'Sisa saldo setelah ditarik'],
        #     'Nominal': [initial_balance, total_escrow_amount, escrow_amount, remaining_balance]
        # })

        # st.markdown("### Escrow Balance Calculation")
        # st.dataframe(escrow_balance_table)

        # Download as Excel (sum and escrow_balance_table in separate sheets)
        output = io.BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        sum.to_excel(writer, index=False, sheet_name='ProcessedData')       
        workbook=writer.book
        worksheet=writer.sheets['ProcessedData']
        # with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        #     sum.to_excel(writer, index=False, sheet_name='ProcessedData')
            # escrow_balance_table.to_excel(writer, index=False, sheet_name='Escrow_Balance')
        writer.save()
        output.seek(0)
        st.download_button(
            label="Download Processed Data (Excel)",
            data=output,
            file_name='processed_data.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )



