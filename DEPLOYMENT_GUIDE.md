# Deployment Guide - Salehi Panel

This guide provides step-by-step instructions for deploying updates to the production server.

---

## 📦 Latest Update (2026-02-16): Dashboard Fixes & API Updates

### What's Changed

**Critical Bug Fixes:**
1. ✅ Fixed dashboard white page crash (TypeScript interface mismatch)
2. ✅ Fixed infinite redirect to login on page refresh (auth race condition)
3. ✅ Fixed 500 error on `/api/stats/costs` endpoint (missing company parameter)

**Files Modified:**
- `frontend/src/pages/Dashboard.tsx` - Fixed stats.totals interface
- `frontend/src/hooks/useCompany.tsx` - Fixed auth loading race condition
- `backend/app/api/stats.py` - Added company filtering to costs endpoint
- `backend/app/services/stats_service.py` - Updated cost_summary to accept company_id and use settings field

### Deployment Steps for Latest Update

#### 1. Pull Latest Code

```bash
# SSH into production server
ssh user@your-production-server

# Navigate to project directory
cd /path/to/salehi-panel

# Stash any local changes (if any)
git stash

# Pull latest code
git pull origin main  # or your branch name

# Check what changed
git log -3 --oneline
git diff HEAD~1 --name-only
```

#### 2. Update Backend

```bash
cd /path/to/salehi-panel/backend

# Activate virtual environment
source ../venv/bin/activate  # Adjust path if different

# Install/update dependencies (if requirements.txt changed)
pip install -r requirements.txt

# Restart backend service
# Choose the appropriate command for your setup:

# Option A: systemd
sudo systemctl restart salehi-panel-backend
sudo systemctl status salehi-panel-backend

# Option B: supervisor
sudo supervisorctl restart salehi-panel-backend
sudo supervisorctl status salehi-panel-backend

# Option C: pm2
pm2 restart salehi-panel-backend
pm2 status

# Option D: manual (if running in screen/tmux)
# 1. Attach to screen/tmux session
# 2. Press Ctrl+C to stop
# 3. Run: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Check backend logs for errors
# systemd:
sudo journalctl -u salehi-panel-backend -f -n 50

# pm2:
pm2 logs salehi-panel-backend --lines 50

# manual logs:
tail -f /var/log/salehi-panel/backend.log  # adjust path as needed
```

#### 3. Update Frontend

```bash
cd /path/to/salehi-panel/frontend

# Install/update dependencies (if package.json changed)
npm install

# Build production version
npm run build

# Deploy to nginx (adjust paths based on your setup)
# Backup current version first
sudo cp -r /var/www/salehi-panel/html /var/www/salehi-panel/html.backup.$(date +%Y%m%d_%H%M%S)

# Deploy new build
sudo rm -rf /var/www/salehi-panel/html/*
sudo cp -r dist/* /var/www/salehi-panel/html/

# Restart nginx (optional, but recommended)
sudo systemctl restart nginx
sudo systemctl status nginx
```

#### 4. Verify Deployment

```bash
# Test backend health
curl -X GET http://localhost:8000/docs
# Should return API documentation page (200 OK)

# Test login endpoint
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"your_admin_user","password":"your_password"}'
# Should return: {"access_token": "..."}

# Test costs endpoint with company parameter
TOKEN="your_token_here"
curl -X GET "http://localhost:8000/api/stats/costs?company=salehi" \
  -H "Authorization: Bearer $TOKEN"
# Should return cost summary (not 500 error)

# Test dashboard-stats endpoint
curl -X GET "http://localhost:8000/api/stats/dashboard-stats?company=salehi&group_by=scenario&time_filter=today" \
  -H "Authorization: Bearer $TOKEN"
# Should return dashboard statistics

# Check frontend
curl -I http://your-domain.com
# Should return 200 OK with HTML content
```

#### 5. Browser Testing

1. **Clear browser cache** (Ctrl+Shift+Delete or Cmd+Shift+Delete)
2. Navigate to `http://your-domain.com/salehi/dashboard`
3. **Expected behavior:**
   - ✅ Should NOT redirect to login (unless not logged in)
   - ✅ Dashboard should load without white screen
   - ✅ Cost summary should display (no 500 error)
   - ✅ Call statistics should display correctly
   - ✅ No errors in browser console (F12)

#### 6. Monitor Logs

```bash
# Monitor backend logs for any errors
sudo journalctl -u salehi-panel-backend -f

# Or if using pm2:
pm2 logs salehi-panel-backend

# Monitor nginx access logs
sudo tail -f /var/log/nginx/access.log

# Monitor nginx error logs
sudo tail -f /var/log/nginx/error.log
```

### Rollback Plan for Latest Update

If issues occur, rollback to previous version:

```bash
# 1. Rollback code
cd /path/to/salehi-panel
git log --oneline -10  # Find previous commit
git checkout <previous-commit-hash>

# 2. Rebuild backend
cd backend
pip install -r requirements.txt
sudo systemctl restart salehi-panel-backend

# 3. Rebuild and redeploy frontend
cd ../frontend
npm install
npm run build
sudo rm -rf /var/www/salehi-panel/html/*
sudo cp -r dist/* /var/www/salehi-panel/html/
sudo systemctl restart nginx

# 4. Or restore frontend from backup
sudo rm -rf /var/www/salehi-panel/html
sudo mv /var/www/salehi-panel/html.backup.YYYYMMDD_HHMMSS /var/www/salehi-panel/html
```

### Success Checklist for Latest Update

- [ ] Code pulled successfully from git
- [ ] Backend restarted without errors
- [ ] Frontend built and deployed successfully
- [ ] Login test passed (curl or browser)
- [ ] Dashboard loads without white screen
- [ ] No redirect to login on page refresh
- [ ] Cost summary displays correctly (no 500 error)
- [ ] No CORS errors in browser console
- [ ] Backend logs show no errors
- [ ] Nginx logs show successful requests

### Technical Details

#### Frontend Changes

**File: `frontend/src/pages/Dashboard.tsx`**
```typescript
// Before (line 40-47):
interface DashboardStats {
  groups: DashboardGroup[]
  totals: {
    total: number
    billable: number
    inbound: number
    statuses: Record<string, number>  // ❌ Wrong - nested structure
  }
}

// After (line 40-42):
interface DashboardStats {
  groups: DashboardGroup[]
  totals: Record<string, number>  // ✅ Correct - flat structure matching backend
}

// Before (line 360):
{(stats.totals.statuses[status] || 0).toLocaleString()}  // ❌ Crashed

// After (line 356):
{(stats.totals[status] || 0).toLocaleString()}  // ✅ Works
```

**File: `frontend/src/hooks/useCompany.tsx`**
```typescript
// Before:
const { user } = useAuth()  // ❌ Missing loading state
useEffect(() => {
  if (!user?.is_superuser && user?.company_name !== companySlug) {
    navigate('/login')  // ❌ Redirects even when user is still loading
  }
}, [user])

// After:
const { user, loading: authLoading } = useAuth()  // ✅ Track auth loading
useEffect(() => {
  if (authLoading) return  // ✅ Wait for auth to complete

  if (!user) {
    navigate('/login')
    return
  }

  if (!user.is_superuser && user.company_name !== companySlug) {
    navigate('/login')
  }
}, [user, authLoading])  // ✅ Dependency on authLoading
```

#### Backend Changes

**File: `backend/app/api/stats.py`**
```python
# Before (line 37-39):
@router.get("/costs", response_model=CostSummary)
def get_costs(db: Session = Depends(get_db)):
    return stats_service.cost_summary(db)  # ❌ No company filtering

# After (line 37-52):
@router.get("/costs", response_model=CostSummary)
def get_costs(
    company: str = Query(..., description="Company slug"),  # ✅ Required parameter
    user: AdminUser = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get cost summary for a company"""
    company_obj = db.query(Company).filter(Company.name == company, Company.is_active == True).first()
    if not company_obj:
        raise HTTPException(status_code=404, detail="Company not found")

    # Verify user has access to this company
    if not user.is_superuser and user.company_id != company_obj.id:
        raise HTTPException(status_code=403, detail="Access denied to this company")

    return stats_service.cost_summary(db, company_obj.id)  # ✅ Pass company_id
```

**File: `backend/app/services/stats_service.py`**
```python
# Before (line 169-176):
def cost_summary(db: Session) -> dict:  # ❌ No company parameter
    cfg = ensure_config(db)
    rate = cfg.cost_per_connected or 0
    # ... queries without company filtering

# After (line 170-177):
def cost_summary(db: Session, company_id: int) -> dict:  # ✅ Accept company_id
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company or not company.settings:  # ✅ Use settings, not billing_config
        rate = 0
    else:
        rate = company.settings.get("cost_per_connected", 0)

    # ... queries WITH company filtering:
    .filter(CallResult.company_id == company_id)  # ✅ Filter by company
```

### Troubleshooting

#### Issue: CORS errors after deployment

**Symptoms:**
```
Access to XMLHttpRequest at 'http://localhost:8000/api/stats/costs?company=salehi'
from origin 'http://localhost:5173' has been blocked by CORS policy
```

**Solution:**
1. Check if backend is running: `curl http://localhost:8000/docs`
2. Verify CORS settings in `backend/app/main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```
3. Restart backend after CORS changes

#### Issue: 500 Error on `/api/stats/costs`

**Symptoms:**
```
AttributeError: 'Company' object has no attribute 'billing_config'
```

**Solution:**
This was fixed in the latest update. Ensure you've pulled the latest code and restarted the backend.

**Verify fix:**
```bash
cd backend
grep -n "billing_config" app/services/stats_service.py
# Should return nothing (or only in comments)

grep -n "company.settings" app/services/stats_service.py
# Should show the corrected code
```

#### Issue: Dashboard redirects to login on refresh

**Symptoms:**
- Dashboard works when navigating from another page
- Redirects to login when refreshing the page directly
- Console shows: "User does not have access to this company"

**Solution:**
This was fixed in the latest update. Ensure frontend has been rebuilt and redeployed.

**Verify fix:**
```bash
cd frontend
grep -A5 "authLoading" src/hooks/useCompany.tsx
# Should show the authLoading check
```

#### Issue: White screen / blank dashboard

**Symptoms:**
- Browser console shows: `Cannot read properties of undefined (reading 'CONNECTED')`
- Dashboard appears completely blank/white

**Solution:**
This was fixed in the latest update. Clear browser cache and hard refresh (Ctrl+Shift+R or Cmd+Shift+R).

**Verify fix in code:**
```bash
cd frontend/src/pages
grep "stats.totals\[status\]" Dashboard.tsx
# Should show: stats.totals[status] (not stats.totals.statuses[status])
```

#### Issue: Backend won't start after update

**Check common issues:**

```bash
# 1. Check if port 8000 is already in use
sudo lsof -i :8000
# If something is using it, kill it: sudo kill -9 <PID>

# 2. Check Python/uvicorn installation
which python3
which uvicorn
# Or: python3 -m uvicorn --version

# 3. Check virtual environment
source ../venv/bin/activate
which python
# Should point to venv python

# 4. Check for syntax errors
cd backend
python3 -m py_compile app/main.py
python3 -m py_compile app/api/stats.py
python3 -m py_compile app/services/stats_service.py

# 5. Check dependencies
pip list | grep -E "fastapi|uvicorn|sqlalchemy"

# 6. Try running manually to see error
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### Issue: Frontend build fails

**Check common issues:**

```bash
# 1. Check Node.js version
node --version
# Should be >= 16.x

# 2. Check npm version
npm --version

# 3. Clear npm cache and reinstall
rm -rf node_modules package-lock.json
npm cache clean --force
npm install

# 4. Check for TypeScript errors
npm run build
# Look for specific error messages

# 5. If TypeScript errors, check the files:
cd frontend/src
grep -n "stats.totals" pages/Dashboard.tsx
grep -n "authLoading" hooks/useCompany.tsx
```

### Environment-Specific Notes

#### Development Environment
```bash
# Backend
cd backend
source ../venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (separate terminal)
cd frontend
npm run dev
```

#### Production Environment (Nginx)
```bash
# Nginx configuration for SPA routing
location / {
    try_files $uri $uri/ /index.html;
}

# Proxy API requests to backend
location /api {
    proxy_pass http://localhost:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

---

## 📋 Multi-Company Migration (Historical Reference)

### ⚠️ Important Pre-Deployment Steps

### 1. Backup Database

**CRITICAL: Always backup your database before running migrations!**

```bash
# SSH into production server
ssh user@your-production-server

# Create backup directory if it doesn't exist
mkdir -p ~/backups

# Backup the database (replace with your actual database name and credentials)
pg_dump -h localhost -U your_db_user -d salehi_panel_db > ~/backups/salehi_panel_backup_$(date +%Y%m%d_%H%M%S).sql

# Verify the backup file exists and has content
ls -lh ~/backups/
```

### 2. Verify Current State

```bash
# Navigate to project directory
cd /path/to/salehi-panel

# Check current git branch and status
git status
git log -1

# Check current migration version
cd backend
source venv/bin/activate  # or your virtual environment activation command
alembic current

# Should show: 0003_superuser_first_admin
```

## 📋 Migration Overview

This migration will:
1. ✅ Create `companies` table (salehi, agrad)
2. ✅ Create `scenarios` table with default scenario for salehi
3. ✅ Create `outbound_lines` table with 4 phone numbers:
   - 02191302954 (خط 1 - تهران)
   - 09422092601 (خط 2 - موبایل)
   - 09422092653 (خط 3 - موبایل)
   - 09422092817 (خط 4 - موبایل)
4. ✅ Rename `phone_numbers` → `numbers`
5. ✅ Rename `call_attempts` → `call_results`
6. ✅ Add company-related columns to existing tables
7. ✅ Assign ALL existing calls to:
   - Company: salehi
   - Scenario: default
   - Outbound lines: distributed equally among the 4 lines
8. ✅ Add performance indexes for fast queries on large datasets (1.9M+ records)

## 🚀 Deployment Steps

### Step 1: Pull Latest Code

```bash
# Navigate to project directory
cd /path/to/salehi-panel

# Pull latest code from git
git pull origin main

# Or if you're on a different branch
git checkout main
git pull
```

### Step 2: Update Backend Dependencies

```bash
cd backend

# Activate virtual environment
source venv/bin/activate  # Adjust if using different venv path

# Install/update dependencies
pip install -r requirements.txt

# Verify alembic is working
alembic --help
```

### Step 3: Run Database Migration

```bash
# Still in backend directory with venv activated

# Check what migrations will be applied
alembic upgrade --sql head > /tmp/migration_preview.sql
cat /tmp/migration_preview.sql

# If everything looks good, run the migration
alembic upgrade head

# Expected output should end with:
# INFO  [alembic.runtime.migration] Running upgrade 0003_superuser_first_admin -> 0004_multi_company, multi-company support with scenarios and outbound lines
```

### Step 4: Verify Migration

```bash
# Check current migration version
alembic current
# Should show: 0004_multi_company

# Connect to database and verify tables
psql -h localhost -U your_db_user -d salehi_panel_db

# Run verification queries:
```

```sql
-- Check companies were created
SELECT * FROM companies;
-- Expected: 2 rows (salehi, agrad)

-- Check scenarios were created
SELECT * FROM scenarios;
-- Expected: 1 row (default scenario for salehi)

-- Check outbound lines were created
SELECT * FROM outbound_lines ORDER BY id;
-- Expected: 4 rows (4 phone numbers for salehi)

-- Verify all call_results have company_id assigned
SELECT
    COUNT(*) as total_calls,
    COUNT(company_id) as calls_with_company,
    COUNT(scenario_id) as calls_with_scenario,
    COUNT(outbound_line_id) as calls_with_line
FROM call_results;
-- All counts should be equal

-- Verify equal distribution of calls among outbound lines
SELECT
    ol.phone_number,
    ol.display_name,
    COUNT(cr.id) as call_count
FROM outbound_lines ol
LEFT JOIN call_results cr ON cr.outbound_line_id = ol.id
GROUP BY ol.id, ol.phone_number, ol.display_name
ORDER BY call_count DESC;
-- Should show roughly equal distribution

-- Verify indexes were created
SELECT indexname, tablename
FROM pg_indexes
WHERE tablename IN ('numbers', 'call_results', 'companies', 'scenarios', 'outbound_lines')
ORDER BY tablename, indexname;

-- Exit psql
\q
```

### Step 5: Restart Backend Service

```bash
# Restart the backend service (adjust command based on your setup)

# If using systemd:
sudo systemctl restart salehi-panel-backend

# If using supervisor:
sudo supervisorctl restart salehi-panel-backend

# If using pm2:
pm2 restart salehi-panel-backend

# If running in screen/tmux, you'll need to manually stop and restart

# Check service status
sudo systemctl status salehi-panel-backend
# Or
pm2 status

# Check logs for any errors
sudo journalctl -u salehi-panel-backend -f
# Or
pm2 logs salehi-panel-backend
```

### Step 6: Update Frontend (if applicable)

```bash
cd /path/to/salehi-panel/frontend

# Install dependencies (if package.json changed)
npm install

# Build production version
npm run build

# Deploy to nginx (adjust path based on your setup)
sudo rm -rf /var/www/salehi-panel/html/*
sudo cp -r dist/* /var/www/salehi-panel/html/

# Restart nginx
sudo systemctl restart nginx
```

### Step 7: Smoke Test

```bash
# Test the API is responding
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"your_admin_user","password":"your_password"}'

# Should return a token

# Test company endpoint
curl -X GET http://localhost:8000/api/companies \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Should return companies list
```

## ✅ Post-Deployment Verification

### 1. Database Verification

Log into PostgreSQL and run these verification queries:

```sql
-- 1. Verify table renames
SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'numbers');
-- Should return: t (true)

SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'phone_numbers');
-- Should return: f (false)

SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'call_results');
-- Should return: t (true)

SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'call_attempts');
-- Should return: f (false)

-- 2. Verify data integrity
SELECT
    c.name as company_name,
    COUNT(cr.id) as total_calls,
    COUNT(DISTINCT cr.scenario_id) as unique_scenarios,
    COUNT(DISTINCT cr.outbound_line_id) as unique_lines,
    MIN(cr.attempted_at) as first_call,
    MAX(cr.attempted_at) as last_call
FROM companies c
LEFT JOIN call_results cr ON cr.company_id = c.id
GROUP BY c.id, c.name;

-- 3. Verify outbound line distribution
SELECT
    ol.phone_number,
    COUNT(cr.id) as call_count,
    ROUND(COUNT(cr.id) * 100.0 / SUM(COUNT(cr.id)) OVER (), 2) as percentage
FROM outbound_lines ol
LEFT JOIN call_results cr ON cr.outbound_line_id = ol.id
GROUP BY ol.id, ol.phone_number
ORDER BY call_count DESC;
-- Each line should have approximately 25% of calls

-- 4. Verify performance indexes
EXPLAIN ANALYZE
SELECT * FROM numbers
WHERE global_status = 'ACTIVE'
  AND (last_called_at IS NULL OR last_called_at < NOW() - INTERVAL '3 days')
LIMIT 100;
-- Should use index scan, not sequential scan
-- Execution time should be < 100ms
```

### 2. Application Verification

1. **Login Test**: Try logging in with your admin credentials
2. **Dashboard Test**: Navigate to dashboard and verify data is displayed
3. **Numbers Test**: Check that numbers page shows the numbers
4. **Schedule Test**: Verify schedule configuration is intact
5. **Billing Test**: Verify billing/wallet information is preserved

### 3. Monitor Logs

```bash
# Monitor application logs for any errors
tail -f /var/log/salehi-panel/backend.log

# Monitor database logs
sudo tail -f /var/log/postgresql/postgresql-*.log

# Monitor nginx logs
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

## 🔄 Rollback Plan

If something goes wrong, follow these steps:

### Option 1: Database Rollback (Recommended if data integrity is compromised)

```bash
cd /path/to/salehi-panel/backend
source venv/bin/activate

# Rollback the migration
alembic downgrade -1

# Verify
alembic current
# Should show: 0003_superuser_first_admin

# Restart backend service
sudo systemctl restart salehi-panel-backend
```

### Option 2: Full Restore from Backup (If rollback fails)

```bash
# Stop the backend service
sudo systemctl stop salehi-panel-backend

# Restore from backup
psql -h localhost -U your_db_user -d salehi_panel_db < ~/backups/salehi_panel_backup_YYYYMMDD_HHMMSS.sql

# Verify restore
psql -h localhost -U your_db_user -d salehi_panel_db -c "SELECT COUNT(*) FROM call_attempts;"

# Restart backend service
sudo systemctl start salehi-panel-backend
```

### Option 3: Code Rollback

```bash
cd /path/to/salehi-panel

# Checkout previous version
git log  # Find the commit hash before migration
git checkout <previous-commit-hash>

# Rebuild and restart
cd backend
pip install -r requirements.txt
sudo systemctl restart salehi-panel-backend

cd ../frontend
npm install
npm run build
sudo cp -r dist/* /var/www/salehi-panel/html/
sudo systemctl restart nginx
```

## 📊 Performance Monitoring

After deployment, monitor these metrics:

```sql
-- Query performance check (should be < 200ms)
EXPLAIN ANALYZE
SELECT
    scenario_id,
    status,
    COUNT(*)
FROM call_results
WHERE company_id = 1
  AND attempted_at >= CURRENT_DATE
GROUP BY scenario_id, status;

-- Table sizes
SELECT
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Index usage statistics
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;
```

## 📝 Migration Summary

### What Changed:

**Database:**
- ✅ Added 3 new tables: `companies`, `scenarios`, `outbound_lines`
- ✅ Renamed 2 tables: `phone_numbers` → `numbers`, `call_attempts` → `call_results`
- ✅ Added 3 new ENUM types: `globalstatus`, `agenttype`, `INBOUND_CALL` to `callstatus`
- ✅ Added company-related columns to: `admin_users`, `numbers`, `call_results`, `schedule_configs`, `schedule_windows`
- ✅ Created 8 new indexes for performance optimization

**Data:**
- ✅ Created 2 companies: salehi, agrad
- ✅ Created 1 default scenario for salehi
- ✅ Created 4 outbound lines for salehi with phone numbers
- ✅ Assigned ALL existing calls to salehi company
- ✅ Assigned ALL existing calls to default scenario
- ✅ Distributed ALL existing calls equally among 4 outbound lines
- ✅ Assigned ALL non-superuser admin users to salehi company

### What Did NOT Change:

- ❌ No data loss - all existing calls, numbers, users, schedules are preserved
- ❌ No application downtime required during migration (tables renamed atomically)
- ❌ No changes to authentication mechanism
- ❌ No changes to existing API endpoints (they still work with old paths)

## 🆘 Troubleshooting

### Issue: Migration fails with "column already exists"

**Solution:**
```bash
# Check if migration was partially applied
psql -h localhost -U your_db_user -d salehi_panel_db

# Check which columns exist
\d+ admin_users
\d+ numbers
\d+ call_results

# If some changes were applied, you may need to manually rollback or apply missing parts
```

### Issue: Foreign key constraint violation

**Solution:**
This shouldn't happen if migration runs completely, but if it does:
```sql
-- Check for orphaned records
SELECT COUNT(*) FROM call_results WHERE company_id IS NOT NULL AND company_id NOT IN (SELECT id FROM companies);
SELECT COUNT(*) FROM admin_users WHERE company_id IS NOT NULL AND company_id NOT IN (SELECT id FROM companies);

-- If found, set them to NULL or assign to salehi
UPDATE call_results SET company_id = NULL WHERE company_id NOT IN (SELECT id FROM companies);
```

### Issue: Performance degradation

**Solution:**
```sql
-- Vacuum and analyze tables
VACUUM ANALYZE numbers;
VACUUM ANALYZE call_results;
VACUUM ANALYZE companies;
VACUUM ANALYZE scenarios;
VACUUM ANALYZE outbound_lines;

-- Rebuild indexes if needed
REINDEX TABLE numbers;
REINDEX TABLE call_results;
```

### Issue: Backend won't start after migration

**Solution:**
```bash
# Check logs
sudo journalctl -u salehi-panel-backend -n 100

# Common issues:
# 1. Database connection error - check credentials in .env
# 2. Import error - check all new model files are present
# 3. Alembic version mismatch - run: alembic stamp head
```

## 📞 Support

If you encounter issues not covered in this guide:

1. Check application logs: `/var/log/salehi-panel/`
2. Check database logs: `/var/log/postgresql/`
3. Verify database state with the verification queries above
4. Consider rolling back and re-attempting deployment
5. Restore from backup if data integrity is compromised

## ✅ Success Checklist

- [ ] Database backup created and verified
- [ ] Migration executed successfully (`alembic upgrade head`)
- [ ] All verification queries return expected results
- [ ] Backend service restarted and running
- [ ] Frontend deployed (if applicable)
- [ ] Login test passed
- [ ] Dashboard displays data correctly
- [ ] No errors in application logs
- [ ] Database query performance is acceptable (< 200ms for stats queries)
- [ ] Companies table has 2 rows (salehi, agrad)
- [ ] Scenarios table has 1 row (default for salehi)
- [ ] Outbound lines table has 4 rows (4 phone numbers)
- [ ] All call_results have company_id, scenario_id, outbound_line_id
- [ ] Calls are distributed roughly equally among 4 outbound lines

---

**Deployment Date:** ___________

**Deployed By:** ___________

**Database Backup Location:** ___________

**Notes:** ___________
