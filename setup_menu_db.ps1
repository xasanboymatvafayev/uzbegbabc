# ============================================================
#  Fast Food Menu - PostgreSQL Setup (PowerShell)
#  Ishlatish: .\setup_menu_db.ps1
# ============================================================

# ---------- SOZLAMALAR (o'zgartiring) ----------
$PG_HOST     = "postgres.railway.internal"
$PG_PORT     = "5432"
$PG_USER     = "postgres"
$PG_PASSWORD = "ZYQtvsNytbMvAxQQsAwmCbNGMiDuAvVU"     # <-- o'z parolingizni kiriting
$PG_DB       = "railway"
# ------------------------------------------------

$env:PGPASSWORD = $PG_PASSWORD

# psql ni topish
$psqlPaths = @(
    "psql",
    "C:\Program Files\PostgreSQL\17\bin\psql.exe",
    "C:\Program Files\PostgreSQL\16\bin\psql.exe",
    "C:\Program Files\PostgreSQL\15\bin\psql.exe"
)
$psql = $null
foreach ($p in $psqlPaths) {
    if (Get-Command $p -ErrorAction SilentlyContinue) { $psql = $p; break }
    if (Test-Path $p) { $psql = $p; break }
}
if (-not $psql) {
    Write-Error "psql topilmadi! PostgreSQL o'rnatilganini tekshiring."
    exit 1
}

Write-Host ""
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "   Fast Food Menu - DB Setup           " -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan

# ---------- 1. Databaza yaratish ----------
Write-Host "`n[1/3] '$PG_DB' databazasi yaratilmoqda..." -ForegroundColor Yellow
& $psql -h $PG_HOST -p $PG_PORT -U $PG_USER -d postgres `
    -c "CREATE DATABASE $PG_DB;" 2>$null

if ($LASTEXITCODE -eq 0) {
    Write-Host "      OK - Databaza yaratildi." -ForegroundColor Green
} else {
    Write-Host "      Databaza allaqachon mavjud, davom etilmoqda..." -ForegroundColor Gray
}

# ---------- 2. SQL skriptni ishga tushirish ----------
Write-Host "`n[2/3] Jadvallar va ma'lumotlar qo'shilmoqda..." -ForegroundColor Yellow

$sqlFile = Join-Path $PSScriptRoot "menu_setup.sql"
if (-not (Test-Path $sqlFile)) {
    Write-Error "menu_setup.sql topilmadi: $sqlFile"
    exit 1
}

& $psql -h $PG_HOST -p $PG_PORT -U $PG_USER -d $PG_DB -f $sqlFile

if ($LASTEXITCODE -ne 0) {
    Write-Error "SQL skriptni bajarishda xatolik!"
    exit 1
}
Write-Host "      OK - Ma'lumotlar qo'shildi." -ForegroundColor Green

# ---------- 3. Natijani ko'rsatish ----------
Write-Host "`n[3/3] Natija:" -ForegroundColor Yellow

& $psql -h $PG_HOST -p $PG_PORT -U $PG_USER -d $PG_DB -c `
"SELECT c.name AS Kategoriya, COUNT(m.id) AS Taomlar, MIN(m.price) AS MinNarx, MAX(m.price) AS MaxNarx
 FROM categories c LEFT JOIN menu_items m ON c.id = m.category_id
 GROUP BY c.name, c.id ORDER BY c.id;"

Write-Host ""
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "   Hammasi tayyor!                     " -ForegroundColor Green
Write-Host "   Databaza : $PG_DB"                    -ForegroundColor White
Write-Host "   Ulanish  : psql -U $PG_USER -d $PG_DB" -ForegroundColor White
Write-Host "=======================================" -ForegroundColor Cyan
