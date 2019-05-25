rm -f dist/example_pkg_your_bobstein-*
rm -f dist/example-pkg-your-bobstein-*
py -3.7 version_update_now.py || goto bad
py -3.7 setup.py sdist bdist_wheel || goto bad

setlocal
set /p REPO=<secure\pypi.repo.txt
set /p USER=<secure\pypi.user.txt
set /p PASS=<secure\pypi.pass.txt
py -3.7 -m twine upload --repository-url %REPO% -u %USER% -p %PASS% dist/* || goto bad
endlocal

echo SUCCESS
goto fin
:bad
echo FAILURE
:fin
