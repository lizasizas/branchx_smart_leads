import io
import hashlib
from datetime import date, timedelta
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title='BranchX Smart Leads', page_icon='🏦', layout='wide', initial_sidebar_state='expanded')
COLS=['CIF','Status','Nama Nasabah','Nama Produk','Inisiatif','Sub Inisiatif','Nama Perusahaan','Tanggal Upload','Tanggal Expired','Keterangan 1','Keterangan 2','Keterangan 3','Kategori Lead','Limit Indikatif','Assign To','Assign By','Assign Date','Kode Cabang','Kode Kawasan','Kode Area','Kode Region']
STATUSES=['Assigned','Followup','New','Old','Reassigned','Referral','To be reffered']
CATEGORIES=['Business Case','GMM','Hotlead','Reguler','Reoffer']
PRODUCTS=['Credit Card','AXA Insurance','Personal Loan','Savings','Payroll']
PICS=['PIC A','PIC B','PIC C','PIC D']

st.markdown('''<style>
.block-container{padding-top:1.7rem;padding-bottom:2rem}
h1,h2,h3{color:#142b49}
[data-testid="stMetric"]{background:#f1f5fa;border:1px solid #e0e8f2;border-radius:13px;padding:14px}
[data-testid="stSidebar"]{background:#10243e}
[data-testid="stSidebar"] *{color:#eef5ff!important}
[data-testid="stSidebar"] input{color:#142b49!important}
.hero{background:linear-gradient(110deg,#10243e,#24547d);color:white;padding:26px;border-radius:16px;margin-bottom:18px}
.hero h1{color:white;margin:0;font-size:2rem}.hero p{color:#d4e4f4;margin:7px 0 0}
.small-note{color:#6c7b8d;font-size:.84rem}
</style>''',unsafe_allow_html=True)

@st.cache_data
def synthetic_data():
    rng=np.random.default_rng(2026)
    names=['Andi Pratama','Budi Santoso','Citra Dewi','Dian Mahendra','Eka Putri','Fajar Nugroho','Gita Lestari','Hendra Wijaya','Intan Sari','Joko Saputra','Kartika Ayu','Lukman Hakim']
    companies=['PT Nusantara Maju','PT Sinar Abadi','PT Mitra Sejahtera','PT Cakrawala','']
    today=date.today(); rows=[]
    for i in range(220):
        cif=f'SYN-{i+1:05d}'
        count=int(rng.choice([1,2,3,4],p=[.51,.31,.14,.04]))
        chosen=rng.choice(PRODUCTS,size=count,replace=False)
        base_pic=str(rng.choice(PICS))
        for j,product in enumerate(chosen):
            status=str(rng.choice(STATUSES,p=[.25,.17,.25,.10,.08,.08,.07]))
            cat=str(rng.choice(CATEGORIES,p=[.12,.10,.19,.48,.11]))
            upload=today-timedelta(days=int(rng.integers(1,75)))
            expiry=today+timedelta(days=int(rng.integers(-18,65)))
            pic=base_pic if j==0 or rng.random()<.62 else str(rng.choice(PICS))
            remarks=['Payroll' if rng.random()<.35 else 'Individu','Kartu kredit aktif' if rng.random()<.25 else '','100-500 Jt' if rng.random()<.15 else '']
            rows.append([cif,status,names[i%len(names)]+f' {i//len(names)+1}',str(product),'Cross Sell','EDA Prospect',str(rng.choice(companies)),upload.isoformat(),expiry.isoformat(),*remarks,cat,int(rng.choice([0,50000000,100000000,250000000])),pic,'Team Lead',(upload+timedelta(days=1)).isoformat(),'BR001','K01','A01','R01'])
    df=pd.DataFrame(rows,columns=COLS)
    # Illustrative invalid data for quality testing, not real customer data.
    df.loc[3,'CIF']=''
    df.loc[14,'Tanggal Expired']='not-a-date'
    df.loc[25,'Assign To']=''
    return df

def normalize(df):
    out=df.copy()
    for col in COLS:
        if col not in out: out[col]=''
    out=out[COLS]
    for col in COLS:
        if col not in ['Limit Indikatif']:
            out[col]=out[col].fillna('').astype(str).str.strip()
    for col in ['Tanggal Upload','Tanggal Expired','Assign Date']:
        out[col+'_parsed']=pd.to_datetime(out[col].replace('',pd.NA),errors='coerce',dayfirst=False).dt.date
    out['CIF_key']=out['CIF'].str.upper()
    out['missing_cif']=out['CIF_key'].eq('')
    out['invalid_expiry']=out['Tanggal Expired_parsed'].isna()
    today=date.today()
    out['days_left']=out['Tanggal Expired_parsed'].apply(lambda d:(d-today).days if pd.notna(d) else np.nan)
    out['expired']=out['days_left'].lt(0).fillna(False)
    out['missing_pic']=out['Assign To'].eq('')
    # Priority is urgency-based, not conversion likelihood. Contact eligibility is NOT asserted.
    def classify(r):
        if r['missing_cif']: return 'DATA REVIEW','Missing CIF'
        if r['invalid_expiry']: return 'DATA REVIEW','Invalid/missing expiry date'
        if r['expired']: return 'HOLD','Expired lead'
        if r['days_left']<=7: return 'HIGH','Expires within 7 days'
        if r['days_left']<=30: return 'MEDIUM','Expires within 8–30 days'
        return 'STANDARD','Expires after 30 days'
    results=out.apply(classify,axis=1)
    out['Priority']=[x[0] for x in results]
    out['Priority Reason']=[x[1] for x in results]
    out['Workflow Flag']=out['Status'].map({'Followup':'Verify follow-up schedule','Old':'Review freshness','Reassigned':'Check assignment change','Referral':'Review referral workflow','To be reffered':'Review referral destination'}).fillna('')
    out['Category Flag']=out['Kategori Lead'].map({'Hotlead':'Confirm Hotlead definition','GMM':'Confirm GMM definition','Business Case':'Check business-case policy','Reoffer':'Review prior offer/contact restrictions'}).fillna('')
    valid=out[~out['missing_cif']]
    pic_counts=valid.groupby('CIF_key')['Assign To'].apply(lambda x:x[x.ne('')].nunique())
    prod_counts=valid.groupby('CIF_key')['Nama Produk'].nunique()
    out['Distinct PICs']=out['CIF_key'].map(pic_counts).fillna(0).astype(int)
    out['Distinct Products']=out['CIF_key'].map(prod_counts).fillna(0).astype(int)
    out['PIC Conflict']=out['Distinct PICs'].gt(1)
    return out

@st.cache_data
def load_bytes(raw,filename):
    if filename.lower().endswith('.csv'):
        try: return pd.read_csv(io.BytesIO(raw),dtype=str,encoding='utf-8-sig')
        except UnicodeDecodeError: return pd.read_csv(io.BytesIO(raw),dtype=str,encoding='cp1252')
    return pd.read_excel(io.BytesIO(raw),dtype=str)

if 'assignments' not in st.session_state: st.session_state.assignments={}
if 'contact_logs' not in st.session_state: st.session_state.contact_logs=[]

with st.sidebar:
    st.markdown('## 🏦 BranchX')
    st.caption('SMART LEADS · OJT DEMO')
    st.divider()
    st.markdown('**Data source**')
    source=st.radio('Choose dataset', ['Synthetic demo (recommended)','Upload authorized test file'],label_visibility='collapsed')
    uploaded=None
    if source.startswith('Upload'):
        st.warning('Use only synthetic or bank-approved non-sensitive test data. Do NOT upload actual customer data to public Streamlit hosting.')
        approved=st.checkbox('I confirm this file is synthetic or approved for this deployment')
        if approved: uploaded=st.file_uploader('CSV or XLSX',type=['csv','xlsx'])
    st.divider()
    st.caption('Priority logic: ≤7 days HIGH · 8–30 MEDIUM · >30 STANDARD. Expired HOLD. Invalid DATA REVIEW.')
    st.caption('No ML · No bank integration · No automated customer contact')

try:
    if uploaded is not None:
        raw=load_bytes(uploaded.getvalue(),uploaded.name)
        if not set(['CIF','Tanggal Expired']).issubset(raw.columns):
            st.error('Required columns missing: CIF and/or Tanggal Expired.');st.stop()
        dataset_label='Authorized test upload'
    else:
        raw=synthetic_data();dataset_label='Synthetic demo data'
    df=normalize(raw)
except Exception as e:
    st.error(f'Unable to read file: {e}');st.stop()

st.markdown('<div class="hero"><h1>BranchX Smart Leads</h1><p>From Data Overload to Actionable Leads · Intelligent Lead Orchestration</p></div>',unsafe_allow_html=True)
st.caption(f'🧪 {dataset_label}  |  {len(df):,} records  |  Updated for demo on {date.today():%d %b %Y}  |  All priority rules are proposed, not official bank policy')

tabs=st.tabs(['📊 Executive Overview','🧹 Data Quality','🎯 Priority Queue','🤝 PIC Coordination','📈 Impact Measurement','⚙️ Rules & Guide'])
with tabs[0]:
    unique=int(df.loc[~df['missing_cif'],'CIF_key'].nunique())
    excess=int((~df['missing_cif']).sum()-unique)
    conflict_cifs=int(df.loc[df['PIC Conflict'],'CIF_key'].nunique())
    a,b,c,d,e=st.columns(5)
    a.metric('Total records',f'{len(df):,}')
    b.metric('Unique CIF',f'{unique:,}')
    c.metric('Excess CIF records',f'{excess:,}')
    d.metric('Expired records',f'{int(df.expired.sum()):,}')
    e.metric('Multi-PIC CIF',f'{conflict_cifs:,}')
    st.info('Excess CIF records represent additional product/lead rows, not necessarily erroneous duplicates. Multi-PIC is an assignment conflict flag, not proof of repeated customer contact.')
    x,y=st.columns(2)
    with x:
        counts=df['Priority'].value_counts().rename_axis('Priority').reset_index(name='Records')
        fig=px.bar(counts,x='Priority',y='Records',text='Records',color='Priority',color_discrete_map={'HIGH':'#0d9488','MEDIUM':'#3b82f6','STANDARD':'#64748b','HOLD':'#e57c46','DATA REVIEW':'#bd5365'})
        fig.update_layout(showlegend=False,margin=dict(l=10,r=10,t=30,b=10),title='Operational Priority Distribution')
        st.plotly_chart(fig,use_container_width=True)
    with y:
        p=df['Nama Produk'].value_counts().head(10).rename_axis('Product').reset_index(name='Records')
        fig=px.bar(p,x='Records',y='Product',orientation='h',title='Product Opportunities',color_discrete_sequence=['#24547d'])
        fig.update_layout(margin=dict(l=10,r=10,t=30,b=10),yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig,use_container_width=True)
    st.subheader('Lead snapshot')
    st.dataframe(df[['CIF','Nama Nasabah','Nama Produk','Status','Kategori Lead','Tanggal Expired','Assign To','Priority','Priority Reason']].head(20),use_container_width=True,hide_index=True)

with tabs[1]:
    st.subheader('Data validation & customer consolidation')
    q1,q2,q3,q4=st.columns(4)
    q1.metric('Missing CIF',int(df.missing_cif.sum()))
    q2.metric('Invalid expiry',int(df.invalid_expiry.sum()))
    q3.metric('Unassigned records',int(df.missing_pic.sum()))
    q4.metric('Multi-product CIF',int(df.loc[df['Distinct Products']>1,'CIF_key'].nunique()))
    problems=df[df[['missing_cif','invalid_expiry','missing_pic']].any(axis=1)]
    st.markdown('**Records requiring data review**')
    st.dataframe(problems[['CIF','Nama Nasabah','Nama Produk','Tanggal Expired','Assign To','missing_cif','invalid_expiry','missing_pic']],use_container_width=True,hide_index=True)
    st.markdown('**Customer 360 Lite — all opportunities retained**')
    choices=sorted(df.loc[~df.missing_cif,'CIF_key'].unique().tolist())
    chosen=st.selectbox('Select CIF',choices,key='quality_cif')
    view=df[df.CIF_key.eq(chosen)]
    st.write(f'**{len(view)} lead records · {view["Nama Produk"].nunique()} distinct products · {view["Assign To"].replace("",pd.NA).nunique()} assigned PICs**')
    st.dataframe(view[['CIF','Nama Nasabah','Nama Produk','Status','Kategori Lead','Tanggal Expired','Assign To','Priority']],use_container_width=True,hide_index=True)
    st.download_button('⬇️ Export data quality review CSV',problems[COLS].to_csv(index=False).encode('utf-8-sig'),'branchx_data_review.csv','text/csv')

with tabs[2]:
    st.subheader('Actionable priority queue')
    st.caption('Priority is driven by expiry urgency after basic validation. It does NOT measure conversion probability or authorize customer outreach.')
    f1,f2,f3,f4=st.columns(4)
    pri=f1.multiselect('Priority',['HIGH','MEDIUM','STANDARD','HOLD','DATA REVIEW'],default=['HIGH','MEDIUM','STANDARD'])
    prod=f2.multiselect('Product',sorted(df['Nama Produk'].dropna().unique()))
    stat=f3.multiselect('EDA Status',sorted(df['Status'].dropna().unique()))
    pic=f4.multiselect('Assigned PIC',sorted(df['Assign To'].dropna().unique()))
    filtered=df[df['Priority'].isin(pri)]
    if prod: filtered=filtered[filtered['Nama Produk'].isin(prod)]
    if stat: filtered=filtered[filtered['Status'].isin(stat)]
    if pic: filtered=filtered[filtered['Assign To'].isin(pic)]
    filtered=filtered.copy();filtered['priority_order']=filtered['Priority'].map({'HIGH':0,'MEDIUM':1,'STANDARD':2,'HOLD':3,'DATA REVIEW':4})
    filtered=filtered.sort_values(['priority_order','days_left'],na_position='last')
    st.metric('Matching opportunities',len(filtered))
    st.dataframe(filtered[['CIF','Nama Nasabah','Nama Produk','Status','Kategori Lead','Tanggal Expired','days_left','Assign To','Priority','Priority Reason','Workflow Flag','Category Flag','PIC Conflict']],use_container_width=True,hide_index=True)
    st.download_button('⬇️ Export filtered queue',filtered[COLS+['Priority','Priority Reason','Workflow Flag','Category Flag','PIC Conflict']].to_csv(index=False).encode('utf-8-sig'),'branchx_priority_queue.csv','text/csv')

with tabs[3]:
    st.subheader('PIC assignment conflict & coordination')
    conflicts=df[df['PIC Conflict'] & ~df['missing_cif']]
    conflict_ids=sorted(conflicts['CIF_key'].unique().tolist())
    st.metric('CIF with >1 distinct assigned PIC',len(conflict_ids))
    st.caption('This identifies potential assignment coordination issues, not confirmed duplicate outreach.')
    if conflict_ids:
        selection=st.selectbox('Choose conflict CIF',conflict_ids)
        customer=df[df.CIF_key.eq(selection)]
        st.dataframe(customer[['Nama Produk','Status','Kategori Lead','Assign To','Assign Date','Tanggal Expired','Priority']],hide_index=True,use_container_width=True)
        available=sorted(set(PICS+customer['Assign To'].dropna().tolist()))
        coordinator=st.selectbox('Proposed contact coordinator',available,index=available.index(st.session_state.assignments.get(selection,available[0])) if st.session_state.assignments.get(selection,available[0]) in available else 0)
        if st.button('Save coordinator (demo session only)'):
            st.session_state.assignments[selection]=coordinator
            st.success(f'{selection} coordinator: {coordinator} (stored only in current session)')
        st.markdown('**Contact log (simulation only)**')
        st.warning('Do not treat this log as bank-authorized contact clearance. No message or call is sent.')
        contact_status=st.selectbox('Simulated activity',['Review completed','Contact attempted','Contact completed','Follow-up needed','Do not contact flag'])
        note=st.text_input('Demo note (no personal information)',placeholder='e.g. coordinator review completed')
        if st.button('Add simulated activity'):
            st.session_state.contact_logs.append({'CIF':selection,'Coordinator':st.session_state.assignments.get(selection,coordinator),'Activity':contact_status,'Note':note,'Logged on':str(date.today())})
            st.success('Demo activity recorded for this session.')
    else: st.info('No multi-PIC conflicts detected in this dataset.')
    if st.session_state.contact_logs:
        st.dataframe(pd.DataFrame(st.session_state.contact_logs),hide_index=True,use_container_width=True)
        st.download_button('⬇️ Export demo contact log',pd.DataFrame(st.session_state.contact_logs).to_csv(index=False).encode('utf-8-sig'),'branchx_demo_contact_log.csv','text/csv')

with tabs[4]:
    st.subheader('Before vs After — measured processing efficiency')
    st.caption('Enter actual timings from a controlled test using the same synthetic dataset and scope. Defaults are illustrative, not observed impact.')
    v1,v2,v3=st.columns(3)
    batch=v1.number_input('Records tested',min_value=1,value=100,step=10)
    manual=v2.number_input('Manual processing (minutes)',min_value=0.0,value=25.0,step=1.0)
    app_time=v3.number_input('Prototype processing incl. review (minutes)',min_value=0.0,value=5.0,step=1.0)
    tested=st.checkbox('These timings were actually measured in a controlled test',value=False)
    saving=manual-app_time
    reduction=(saving/manual*100) if manual>0 else 0
    k1,k2,k3=st.columns(3)
    k1.metric('Time saved',f'{saving:.1f} min')
    k2.metric('Time reduction',f'{reduction:.1f}%')
    k3.metric('Measurement status','Measured' if tested else 'Illustrative')
    fig=px.bar(pd.DataFrame({'Method':['Manual','BranchX prototype'],'Minutes':[manual,app_time]}),x='Method',y='Minutes',text='Minutes',color='Method',color_discrete_sequence=['#8295aa','#0d9488'])
    fig.update_layout(showlegend=False,title=f'Processing time for {batch} records',margin=dict(l=10,r=10,t=35,b=10))
    st.plotly_chart(fig,use_container_width=True)
    st.info('Use actual test results before presenting percentages as achieved impact. Record consolidation and conflict detection are counts, not evidence of additional conversions.')
    report=f'BranchX Smart Leads Impact Test\nStatus: {"Measured" if tested else "Illustrative only"}\nBatch: {batch} records\nManual: {manual:.1f} minutes\nPrototype including review: {app_time:.1f} minutes\nTime saved: {saving:.1f} minutes\nTime reduction: {reduction:.1f}%\n'
    st.download_button('⬇️ Export impact summary',report,'branchx_impact_summary.txt','text/plain')

with tabs[5]:
    st.subheader('Rules, limitations & governance')
    st.markdown('''**Operational priority rules (proposed for demo)**

| Condition | Result | Meaning |
|---|---|---|
| CIF missing | DATA REVIEW | Customer cannot be reliably consolidated |
| Expiry missing/invalid | DATA REVIEW | Validity cannot be established |
| Expired | HOLD | Review/refresh before further action |
| Expires in 0–7 days | HIGH | Urgent expiry review |
| Expires in 8–30 days | MEDIUM | Moderate expiry urgency |
| Expires in >30 days | STANDARD | Standard queue |

**Status** (`New`, `Assigned`, `Followup`, `Old`, `Reassigned`, `Referral`, `To be reffered`) is retained and used for workflow flags, not assumed to represent propensity.

**Kategori Lead** (`Business Case`, `GMM`, `Hotlead`, `Reguler`, `Reoffer`) is retained but **not scored** until bank definitions are confirmed. `Keterangan 1–3` is displayed as-is and not used for scoring because it is unstructured.

**Important:** No consent, do-not-contact, product eligibility, or last-contact field was provided. The app **never labels a lead contact-authorized**. All outreach requires checks in approved bank systems and procedures. `Limit Indikatif` is not used for scoring or eligibility.

**Data privacy:** Public Streamlit Community Cloud is not an approved destination for real customer data by default. Upload synthetic/approved non-sensitive data only. The app does not intentionally persist uploaded files to disk or an external database; hosting platform processing and logs still require review under bank policy. PIC coordination is session-only and not multi-user synchronized.

**Deployment:** Push `app.py`, `requirements.txt`, and optionally `README.md` to a GitHub repository, then deploy `app.py` using Streamlit Community Cloud. Keep the repository free of customer information.
''')
    st.markdown('**Original EDA columns recognized:**')
    st.code(' | '.join(COLS))
