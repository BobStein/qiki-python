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
REM          Solution:  pip install wheel
REM          Also had to update py version codes.
REM          Also had to pip install twine
REM NOTE:  The wheel and twine modules are not included in requirements.txt because those modules
REM        are only required here, to upload qiki-python, not to download and use it.

rmdir /s /q build
rmdir /s /q dist
rmdir /s /q qiki.egg-info
py -3.8 version_update_now.py || goto bad
py -3.8 setup.py sdist bdist_wheel || goto bad

setlocal
set /p REPO=<secure\pypi.repo.txt
set /p USER=<secure\pypi.user.txt
set /p PASS=<secure\pypi.pass.txt
@py -3.8 -m twine upload --repository-url %REPO% -u %USER% -p %PASS% dist/* || goto bad
endlocal

echo SUCCESS
goto fin
:bad
echo FAILURE
:fin
