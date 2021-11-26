@echo off
REM Upload to PyPI
REM --------------
REM 0.  pip install wheel twine
REM 1.  push_to_pypi.bat -- Do this BEFORE github push, because it modifies version.py
REM 2.  github push
REM 3.  gol (for "live" unslumping.org)
REM 4.  gof (for fun.unslumping.org, which handles /meta/oembed/ hits)
REM
REM THANKS:  PyPI instructions, https://packaging.python.org/tutorials/packaging-projects/
REM THANKS:  Batch variable from a file, https://stackoverflow.com/a/2768658/673991
REM THANKS:  Remove stale egg-info, https://stackoverflow.com/a/26547314/673991
REM SEE:  "py" Python Launcher, https://docs.python.org/3/using/windows.html
REM        - Customize installation   <-- when running the Python installer .exe for Windows
REM        - py launcher              <-- check this optional feature
REM THANKS:  error: invalid command 'bdist_wheel'
REM          https://stackoverflow.com/a/44862371/673991
REM          Solution:  pip install wheel twine
REM          Solution:  change py -3.8 to py -3.9
REM          Solution:  install wheel and twine as admin (after uninstalling them as normal)
REM                     (I know, I should use virtual environments, but I don't.)
REM NOTE:  The wheel and twine modules are not included in requirements.txt because those modules
REM        are only required here, to upload qiki-python, not to download and use it.

setlocal
set PY_VER=py -3.9

%PY_VER% -m pip show pip > nul 2> nul
if errorlevel 1 echo install pip (%PY_VER%)
if errorlevel 1 goto bad

%PY_VER% -m pip show wheel > nul 2> nul
if errorlevel 1 echo pip install wheel (%PY_VER%)
if errorlevel 1 goto bad

%PY_VER% -m pip show twine > nul 2> nul
if errorlevel 1 echo pip install twine (%PY_VER%)
if errorlevel 1 goto bad

rmdir /s /q build
rmdir /s /q dist
rmdir /s /q qiki.egg-info
%PY_VER% version_update_now.py || goto bad
%PY_VER% setup.py sdist bdist_wheel || goto bad

set /p REPO=<secure\pypi.repo.txt
set /p USER=<secure\pypi.user.txt
set /p PASS=<secure\pypi.pass.txt
%PY_VER% -m twine upload --repository-url %REPO% -u %USER% -p %PASS% dist/* || goto bad

echo SUCCESS
goto fin
:bad
echo FAILURE
:fin
endlocal
