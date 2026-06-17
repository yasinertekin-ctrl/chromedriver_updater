


@echo off
cd /d "C:\Users\gm-hukuk-6\Desktop\GITHUB\chromedriver_update"

git init
git remote remove origin 2>nul
git remote add origin https://github.com/yasinertekin-ctrl/chromedriver_updater.git
git pull origin main --allow-unrelated-histories
git add .
git commit -m "guncelleme"
git branch -M main
git push -u origin main
 
echo.
echo Tamamlandi!
pause
 