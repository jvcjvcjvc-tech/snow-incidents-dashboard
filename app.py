import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import requests
import json
import os

st.set_page_config(page_title="ServiceNow Incident Dashboard", page_icon="🔴", layout="wide", initial_sidebar_state="expanded")

MAGENTA="#E20074"; BLACK="#000000"; BERRY="#861B54"; DGRAY="#6A6A6A"; LGRAY="#E8E8E8"; TEAL="#0D9488"; AMBER="#F59E0B"

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=DM+Mono&display=swap');
html,body,[class*="css"]{font-family:'DM Sans',sans-serif;}
.main{background:#0a0a0a;}.block-container{padding:1.5rem 2rem 2rem;max-width:1400px;}
section[data-testid="stSidebar"]{background:#111111;border-right:1px solid #222;}
section[data-testid="stSidebar"] *{color:#ccc !important;}
.metric-card{background:#141414;border:1px solid #222;border-radius:12px;padding:20px 24px;text-align:center;}
.metric-val{font-size:42px;font-weight:700;line-height:1;margin:0;}
.metric-lbl{font-size:11px;color:#666;text-transform:uppercase;letter-spacing:0.1em;margin-top:6px;}
.dash-header{background:linear-gradient(135deg,#E20074 0%,#861B54 100%);border-radius:14px;padding:28px 36px;margin-bottom:24px;display:flex;align-items:center;justify-content:space-between;}
.dash-title{font-size:26px;font-weight:700;color:white;margin:0;}
.dash-sub{font-size:13px;color:rgba(255,255,255,0.75);margin-top:4px;}
.dash-badge{background:rgba(0,0,0,0.25);border-radius:20px;padding:6px 16px;font-size:12px;color:white;}
.section-label{font-size:11px;font-weight:600;color:#555;text-transform:uppercase;letter-spacing:0.12em;margin:24px 0 12px;border-bottom:1px solid #1e1e1e;padding-bottom:6px;}
</style>""", unsafe_allow_html=True)

def fetch_from_snow(instance, username, password, limit=100):
    url = f"https://{instance}.service-now.com/api/now/table/incident"
    params = {"sysparm_query":"active=true^state!=6^state!=7","sysparm_display_value":"true","sysparm_exclude_reference_link":"true","sysparm_fields":"number,short_description,state,priority,impact,urgency,assigned_to,assignment_group,caller_id,category,opened_at,sys_updated_on","sysparm_limit":limit}
    try:
        resp = requests.get(url, params=params, auth=(username, password), timeout=15)
        resp.raise_for_status()
        return resp.json().get("result", []), None
    except requests.exceptions.ConnectionError:
        return None, "Connection failed — check your instance name."
    except requests.exceptions.HTTPError as e:
        return None, f"HTTP {e.response.status_code}: {e.response.text[:200]}"
    except Exception as e:
        return None, str(e)

def snow_to_df(records):
    rows = []
    for r in records:
        rows.append({"Number":r.get("number",""),"Description":r.get("short_description",""),"State":r.get("state",""),"Priority":r.get("priority",""),"Impact":r.get("impact",""),"Urgency":r.get("urgency",""),"Assigned To":r.get("assigned_to","") or "Unassigned","Group":r.get("assignment_group","") or "—","Category":r.get("category","") or "—","Caller":r.get("caller_id",""),"Opened":r.get("opened_at","")[:10] if r.get("opened_at") else "","Updated":r.get("sys_updated_on","")[:10] if r.get("sys_updated_on") else ""})
    return pd.DataFrame(rows)

DEMO_DATA = [
    {"Number":"INC118404539","Description":"Job: EpayTNAC_SP_TO_EPAY","State":"New","Priority":"4 - Low","Impact":"3 - Low","Assigned To":"Unassigned","Group":"EFT Application Team","Category":"—","Opened":"2025-08-14","Updated":"2025-08-14"},
    {"Number":"INC115749087","Description":"Expire 25330 submissions - BAN MAX LIMIT","State":"In Progress","Priority":"4 - Low","Impact":"3 - Low","Assigned To":"Bernie Benedicto","Group":"REDDTeam","Category":"—","Opened":"2025-05-09","Updated":"2025-05-09"},
    {"Number":"INC126311299","Description":"NEBULA SCM CDW_NDPSCM_IDW Ended not OK","State":"New","Priority":"4 - Low","Impact":"2 - Medium","Assigned To":"Unassigned","Group":"IDS_SCM_KTLO","Category":"SC Temporary","Opened":"2026-04-18","Updated":"2026-04-21"},
    {"Number":"INC122222946","Description":"Comcast: IPv4 Quarantine Cleanup","State":"New","Priority":"3 - Moderate","Impact":"2 - Medium","Assigned To":"Unassigned","Group":"ATAC Policy","Category":"SC Temporary","Opened":"2025-12-04","Updated":"2025-12-04"},
    {"Number":"INC126236404","Description":"USC0286A BREAKFIX - HIGH TEMP & SMOKE ALARM","State":"New","Priority":"3 - Moderate","Impact":"2 - Medium","Assigned To":"kkey@infinity24-7.com","Group":"PIER_Infinity - Central","Category":"SC Temporary","Opened":"2026-04-15","Updated":"2026-04-17"},
    {"Number":"INC126142263","Description":"DA07245M Nokia eNodeB LTE SiteDegraded Alarm","State":"On Hold","Priority":"3 - Moderate","Impact":"1 - High","Assigned To":"d.bane@bayedcomm.com","Group":"PIER_BayedComm","Category":"SC Temporary","Opened":"2026-04-13","Updated":"2026-04-24"},
    {"Number":"INC1000198142","Description":"All incoming and outgoing calls fail","State":"In Progress","Priority":"4 - Low","Impact":"3 - Low","Assigned To":"Melissa Derrough","Group":"ECS Voice On-Net","Category":"Subscriber","Opened":"2026-04-28","Updated":"2026-04-29"},
    {"Number":"INC123895742","Description":"AIOps: TCP connection failures in OpenCashDrawer","State":"New","Priority":"3 - Moderate","Impact":"2 - Medium","Assigned To":"Unassigned","Group":"AIOps DevOps","Category":"—","Opened":"2026-01-31","Updated":"2026-01-31"},
    {"Number":"INC108763405","Description":"Rebellion Web - 4-digit account PIN invalid","State":"On Hold","Priority":"4 - Low","Impact":"3 - Low","Assigned To":"Unassigned","Group":"PIER_CX Digital","Category":"SC Temporary","Opened":"2024-03-25","Updated":"2025-05-06"},
    {"Number":"INC108678168","Description":"NEPTTN31 Agent System Detection Error","State":"In Progress","Priority":"4 - Low","Impact":"3 - Low","Assigned To":"Kurtis Crowe","Group":"PIER_Probe & Packet","Category":"SC Temporary","Opened":"2024-03-19","Updated":"2024-07-08"},
    {"Number":"INC126394782","Description":"CH38152A Nokia gNodeB 5G SiteDegraded - Chronic","State":"On Hold","Priority":"3 - Moderate","Impact":"1 - High","Assigned To":"Steve Davlantis","Group":"C-GreatLakes-FieldSupport","Category":"SC Temporary","Opened":"2026-04-21","Updated":"2026-04-27"},
    {"Number":"INC124654435","Description":"Indianapolis Switch INBMS001 - Replace AHU 2","State":"New","Priority":"3 - Moderate","Impact":"2 - Medium","Assigned To":"Unassigned","Group":"CFO Central","Category":"SC Temporary","Opened":"2026-02-24","Updated":"2026-02-24"},
    {"Number":"INC112826461","Description":"OMNI POLICY_CONTINUES_WARNING AppDynamics alert","State":"New","Priority":"3 - Moderate","Impact":"3 - Low","Assigned To":"Unassigned","Group":"Digital Commerce Ops","Category":"SC Temporary","Opened":"2024-12-19","Updated":"2024-12-19"},
    {"Number":"INC111727664","Description":"DIGITAL COMMERCE POLICY_CONTINUES_WARNING","State":"New","Priority":"3 - Moderate","Impact":"3 - Low","Assigned To":"Unassigned","Group":"Digital Commerce Ops","Category":"SC Temporary","Opened":"2024-10-27","Updated":"2024-10-27"},
    {"Number":"INC126575486","Description":"9BH1537A Loss of Transport Redundancy at site","State":"New","Priority":"4 - Low","Impact":"2 - Medium","Assigned To":"Gregory Dukes","Group":"S-Deep South-BH-FOPS","Category":"SC Temporary","Opened":"2026-04-29","Updated":"2026-04-29"},
    {"Number":"INC126535133","Description":"PXCOBKP0501 ProtectionJob kAgentError","State":"In Progress","Priority":"4 - Low","Impact":"2 - Medium","Assigned To":"Ramu Nagalla","Group":"EnterpriseBackup","Category":"Enterprise Systems","Opened":"2026-04-27","Updated":"2026-04-28"},
    {"Number":"INC1000195794","Description":"Subscription Billing - Billing/Discount Error","State":"On Hold","Priority":"4 - Low","Impact":"3 - Low","Assigned To":"Kristeljoice Gica","Group":"Billing Operations","Category":"Subscriber","Opened":"2026-04-27","Updated":"2026-04-27"},
    {"Number":"INC126492218","Description":"9ME2123A Nokia MultiTech Non_Service_Impacting","State":"On Hold","Priority":"4 - Low","Impact":"2 - Medium","Assigned To":"Bobby Mitchusson","Group":"S-Deep South-FOPS","Category":"SC Temporary","Opened":"2026-04-25","Updated":"2026-04-25"},
    {"Number":"INC119301784","Description":"TMO NS PROD BAN Recon Organization extraction Failed","State":"On Hold","Priority":"4 - Low","Impact":"3 - Low","Assigned To":"Forrest Glenn","Group":"CUP DigitalOne","Category":"SC Temporary","Opened":"2025-09-09","Updated":"2025-09-12"},
    {"Number":"INC126404997","Description":"BA00902A Compact Flash Removed - Dispatch Required","State":"On Hold","Priority":"4 - Low","Impact":"3 - Low","Assigned To":"Kenneth Dunn","Group":"W-California-SF-FOPS","Category":"SC Temporary","Opened":"2026-04-22","Updated":"2026-04-22"},
]

with st.sidebar:
    st.markdown("## ⚙️ ServiceNow Connection")
    st.markdown("---")
    use_live = st.toggle("Connect to live ServiceNow", value=False)
    if use_live:
        st.markdown("**Instance**")
        instance = st.text_input("", placeholder="your-instance", label_visibility="collapsed")
        st.markdown("**Username**")
        username = st.text_input("", placeholder="admin", label_visibility="collapsed")
        st.markdown("**Password**")
        password = st.text_input("", type="password", placeholder="••••••••", label_visibility="collapsed")
        limit = st.slider("Max records", 10, 500, 100, 10)
        fetch_btn = st.button("🔄 Fetch Incidents", use_container_width=True)
    else:
        st.info("Using demo data (20 incidents). Toggle above to connect live.")
        fetch_btn = False
    st.markdown("---")
    st.markdown("**Filters**")

@st.cache_data(ttl=300)
def load_demo():
    return pd.DataFrame(DEMO_DATA)

if "df" not in st.session_state:
    st.session_state.df = load_demo()
    st.session_state.source = "demo"

if use_live and fetch_btn:
    if not instance or not username or not password:
        st.sidebar.error("Fill in all connection fields.")
    else:
        with st.spinner("Connecting to ServiceNow…"):
            records, err = fetch_from_snow(instance, username, password, limit)
        if err:
            st.sidebar.error(f"❌ {err}")
        else:
            st.session_state.df = snow_to_df(records)
            st.session_state.source = "live"
            st.sidebar.success(f"✅ Loaded {len(st.session_state.df)} incidents")

df = st.session_state.df.copy()

with st.sidebar:
    states = st.multiselect("State", options=sorted(df["State"].unique()), default=list(df["State"].unique()))
    priorities = st.multiselect("Priority", options=sorted(df["Priority"].unique()), default=list(df["Priority"].unique()))
    impacts = st.multiselect("Impact", options=sorted(df["Impact"].unique()), default=list(df["Impact"].unique()))
    if "Group" in df.columns:
        groups_all = ["All"] + sorted(df["Group"].dropna().unique().tolist())
        group_sel = st.selectbox("Assignment Group", groups_all)

mask = df["State"].isin(states) & df["Priority"].isin(priorities) & df["Impact"].isin(impacts)
if "Group" in df.columns and group_sel != "All":
    mask &= df["Group"] == group_sel
df = df[mask]

source_badge = "🟢 Live — ServiceNow" if st.session_state.source == "live" else "🟡 Demo Data"
st.markdown(f"""<div class="dash-header"><div><div class="dash-title">Open Incident Dashboard</div><div class="dash-sub">ServiceNow ITSM · Filtered: {len(df)} incidents · As of {datetime.now().strftime('%B %d, %Y')}</div></div><div class="dash-badge">{source_badge}</div></div>""", unsafe_allow_html=True)

cnt_new=(df["State"]=="New").sum(); cnt_ip=(df["State"]=="In Progress").sum(); cnt_oh=(df["State"]=="On Hold").sum(); cnt_high=(df["Impact"]=="1 - High").sum()
c1,c2,c3,c4,c5=st.columns(5)
for col,val,lbl,color in [(c1,len(df),"Total Open","#E20074"),(c2,cnt_new,"New","#60a5fa"),(c3,cnt_ip,"In Progress","#34d399"),(c4,cnt_oh,"On Hold","#fbbf24"),(c5,cnt_high,"High Impact","#f87171")]:
    col.markdown(f"""<div class="metric-card"><div class="metric-val" style="color:{color}">{val}</div><div class="metric-lbl">{lbl}</div></div>""", unsafe_allow_html=True)

st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
ch1,ch2,ch3=st.columns([1.2,1.2,1.6])
chart_layout=dict(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font_color="#aaa",font_family="DM Sans",margin=dict(l=10,r=10,t=30,b=10),height=240)

with ch1:
    st.markdown("<div class='section-label'>By State</div>", unsafe_allow_html=True)
    sc=df["State"].value_counts().reset_index(); sc.columns=["State","Count"]
    fig=px.pie(sc,names="State",values="Count",hole=0.6,color_discrete_map={"New":MAGENTA,"In Progress":TEAL,"On Hold":AMBER})
    fig.update_layout(**chart_layout); fig.update_traces(textfont_color="white",showlegend=True)
    st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})

with ch2:
    st.markdown("<div class='section-label'>By Priority</div>", unsafe_allow_html=True)
    pc=df["Priority"].value_counts().reset_index(); pc.columns=["Priority","Count"]
    fig2=px.bar(pc,x="Count",y="Priority",orientation="h",color="Priority",color_discrete_map={"3 - Moderate":BERRY,"4 - Low":DGRAY,"2 - High":MAGENTA,"1 - Critical":"#ff0000"})
    fig2.update_layout(**chart_layout,showlegend=False,xaxis=dict(gridcolor="#1e1e1e"),yaxis=dict(gridcolor="rgba(0,0,0,0)"))
    st.plotly_chart(fig2,use_container_width=True,config={"displayModeBar":False})

with ch3:
    st.markdown("<div class='section-label'>Top Assignment Groups</div>", unsafe_allow_html=True)
    if "Group" in df.columns:
        grp=df[df["Group"]!="—"]["Group"].value_counts().head(8).reset_index(); grp.columns=["Group","Count"]; grp["Group"]=grp["Group"].str[:30]
        fig3=px.bar(grp,x="Count",y="Group",orientation="h",color_discrete_sequence=[MAGENTA])
        fig3.update_layout(**chart_layout,showlegend=False,xaxis=dict(gridcolor="#1e1e1e"),yaxis=dict(gridcolor="rgba(0,0,0,0)"))
        st.plotly_chart(fig3,use_container_width=True,config={"displayModeBar":False})

st.markdown("<div class='section-label'>Incident List</div>", unsafe_allow_html=True)
search=st.text_input("🔍 Search incidents",placeholder="Search by number, description, group…",label_visibility="collapsed")
if search:
    mask2=df.apply(lambda row: search.lower() in row.to_string().lower(),axis=1); df=df[mask2]

display_cols=["Number","Description","State","Priority","Impact","Assigned To","Group","Opened"]
display_df=df[display_cols].copy() if all(c in df.columns for c in display_cols) else df.copy()
st.dataframe(display_df,use_container_width=True,height=420,column_config={"Number":st.column_config.TextColumn("Incident #",width="small"),"Description":st.column_config.TextColumn("Description",width="large"),"State":st.column_config.TextColumn("State",width="small"),"Priority":st.column_config.TextColumn("Priority",width="small"),"Impact":st.column_config.TextColumn("Impact",width="small"),"Assigned To":st.column_config.TextColumn("Assigned",width="medium"),"Group":st.column_config.TextColumn("Group",width="medium"),"Opened":st.column_config.TextColumn("Opened",width="small")},hide_index=True)

st.markdown(f"""<div style="margin-top:32px;padding-top:16px;border-top:1px solid #1e1e1e;font-size:11px;color:#444;text-align:center;">T-Mobile Confidential &nbsp;·&nbsp; ServiceNow ITSM &nbsp;·&nbsp; {datetime.now().strftime('%B %d, %Y')}</div>""", unsafe_allow_html=True)
