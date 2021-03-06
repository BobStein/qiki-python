@echo off
REM Upload to PyPI
REM --------------
REM 1.  push_to_pypi.bat -- Do this BEFORE github push, because it modifies version.py
REM 2.  github push
REM 3.  gol (for "live" unslumping.org)
REM 4.  gof (for fun.unslumping.org, which handles /meta/oembed/ hits)
REM
REM THANKS:  PyPI instructions, https://packaging.python.org/tutorials/packaging-projects/
REM THANKS:  Batch variable from a file, https://stackoverflow.com/a/2768658/673991
REM THANKS:  Remove stale egg-info, https://stackoverflow.com/a/26547314/673991

rm -f dist/qiki-*
rm -rf qiki.egg-info
py -3.7 version_update_now.py || goto bad
py -3.7 setup.py sdist bdist_wheel || goto bad

setlocal
set /p REPO=<secure\pypi.repo.txt
set /p USER=<secure\pypi.user.txt
set /p PASS=<secure\pypi.pass.txt
@py -3.7 -m twine upload --repository-url %REPO% -u %USER% -p %PASS% dist/* || goto bad
endlocal

echo SUCCESS
goto fin
:bad
echo FAILURE
:fin
