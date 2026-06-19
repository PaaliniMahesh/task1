# TalentPulse360 - Deployment Guide

## ✅ READY TO DEPLOY - All Configurations Complete!

### Configuration Status:
* ✅ **Warehouse ID**: 855692831808164
* ✅ **Workspace URL**: https://dbc-5207e1d4-6763.cloud.databricks.com
* ✅ **Catalog/Schema**: gold.talentpulse
* ✅ **All 7 Gold Tables Verified** (150 employees each)

---

## 📋 What's Been Fixed:

### 1. **Import Path Issues Fixed**
* ✅ Added sys.path manipulation in app.py for proper imports
* ✅ Fixed db_utils.py to use correct databricks-sql-connector
* ✅ Added error handling for agent endpoint calls

### 2. **Database Connection Updated**
* ✅ Supports both app and notebook environments
* ✅ Handles DATABRICKS_HOST and DATABRICKS_TOKEN env vars
* ✅ Proper URL formatting (removes https:// prefix)

### 3. **Verified Gold Tables** (150 rows each):
* ✅ gold.talentpulse.gold_employee_360
* ✅ gold.talentpulse.gold_employee_ai_features  
* ✅ gold.talentpulse.gold_employee_attendance_summary
* ✅ gold.talentpulse.gold_employee_performance_summary
* ✅ gold.talentpulse.gold_employee_ranking
* ✅ gold.talentpulse.gold_employee_training_summary
* ✅ gold.talentpulse.gold_promotion_readiness

---

## 🚀 Deployment Options

### Option 1: Deploy via Databricks Apps UI (Recommended)

1. **Navigate to Databricks Apps**:
   - Go to: https://dbc-5207e1d4-6763.cloud.databricks.com/ml/apps
   - Click "Create App"

2. **App Configuration**:
   ```
   Name: talentpulse360-assistant
   Source Code Path: /Workspace/Users/mahesh.paalini@bilvantis.io/(Clone) talentpulse360_complete/talentpulse360
   ```

3. **Deploy**:
   - Click "Create" - Databricks will automatically detect `app.yaml`
   - Wait for build and deployment (typically 2-5 minutes)
   - App URL will be provided after successful deployment

### Option 2: Deploy via Databricks CLI

```bash
# Set source directory
cd /Workspace/Users/mahesh.paalini@bilvantis.io/(Clone)\ talentpulse360_complete/talentpulse360

# Create and deploy the app
databricks apps create talentpulse360-assistant \
  --source-code-path . \
  --description "TalentPulse360 AI Employee Assistant"

# Check deployment status
databricks apps get talentpulse360-assistant
```

---

## 📁 File Structure

```
/talentpulse360/
├── app.yaml                    ✅ Databricks App config
├── requirements.txt            ✅ Python dependencies
├── config/
│   └── config.yaml            ✅ App configuration (with warehouse ID)
├── app/
│   ├── app.py                 ✅ Main Streamlit app (imports fixed)
│   └── pages/                 ✅ All 7 page modules
│       ├── chatbot.py
│       ├── employee_search.py
│       ├── attendance.py
│       ├── training.py
│       ├── performance.py
│       ├── skill_gap.py
│       └── workforce.py
├── tools/
│   └── db_utils.py            ✅ Database utilities (fixed)
├── agents/                    ✅ Agent modules (optional for chatbot)
├── rag/                       ✅ RAG components (optional)
└── mlflow_models/             ✅ ML models (optional)
```

---

## ⚙️ App Features After Deployment

### 🤖 **Employee360 Chatbot**
* AI-powered conversational interface
* Natural language queries about employees
* Requires: Agent endpoint to be deployed

### 🔍 **Employee Search**
* Search by name or ID
* 360° employee profiles with radar charts
* Filter by department

### 📅 **Attendance Insights**
* Monthly trends, WFH vs Office
* Low attendance alerts
* Effective hours tracking

### 🎓 **Training Insights**
* Completion rates by employee/department
* Pending trainings dashboard
* Category breakdown

### 🏆 **Performance Insights**
* KRA breakdown and manager ratings
* Top performers leaderboard
* Attendance vs Performance correlation

### 🧩 **Skill Gap Analysis**
* Individual skill assessments
* Missing skills identification
* Recommended learning paths

### 👥 **Workforce Insights**
* Department-wide analytics
* Promotion-ready employees
* At-risk employee identification

---

## 🔑 Required Permissions

Ensure the app has access to:
* ✅ **SQL Warehouse**: 855692831808164
* ✅ **Unity Catalog**: `GRANT USE CATALOG ON gold TO <app_service_principal>`
* ✅ **Schema**: `GRANT USE SCHEMA ON gold.talentpulse TO <app_service_principal>`
* ✅ **Tables**: `GRANT SELECT ON ALL TABLES IN gold.talentpulse TO <app_service_principal>`

---

## 🐛 Troubleshooting

### Issue: "Module not found" errors
* **Cause**: Import path issues
* **Fixed**: ✅ Already resolved in app.py

### Issue: "Cannot connect to warehouse"
* **Cause**: Warehouse not running or permission issues
* **Solution**: Start warehouse 855692831808164 and verify permissions

### Issue: "Agent endpoint not found"
* **Cause**: Endpoint not deployed yet
* **Solution**: Deploy the supervisor agent or disable chatbot page temporarily

### Issue: "Table not found"
* **Cause**: Catalog/schema permissions
* **Solution**: Run permission grants above

---

## 📊 Post-Deployment Testing

Once deployed, test each feature:

1. ✅ **Employee Search**: Search for "Mahesh"
2. ✅ **Attendance**: View monthly trends
3. ✅ **Training**: Check completion rates
4. ✅ **Performance**: View top performers
5. ✅ **Skill Gap**: Analyze gaps by department
6. ✅ **Workforce**: Check promotion-ready employees
7. ⏳ **Chatbot**: Requires agent endpoint (deploy separately)

---

## 🎉 Next Steps After Deployment

1. **Share the app URL** with your team
2. **Set up the AI agent endpoint** for chatbot functionality
3. **Configure permissions** for different user roles
4. **Customize branding** (icon, colors) in config.yaml
5. **Add more visualizations** or custom pages as needed

---

## 📞 Support

If you encounter issues:
1. Check the Databricks Apps logs in the UI
2. Verify warehouse is running and accessible
3. Ensure all tables have data (verified: 150 rows each ✅)
4. Check Unity Catalog permissions

**Current Status**: 🟢 READY TO DEPLOY

**App Root Path**: `/Workspace/Users/mahesh.paalini@bilvantis.io/(Clone) talentpulse360_complete/talentpulse360`
