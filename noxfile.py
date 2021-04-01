import nox

locs = "twitch_py", "noxfile.py"


@nox.session(python=False)
def lint(session):
    session.run("black", *locs)
    session.run("isort", *locs)
    session.run("flake8", *locs)


@nox.session(python=False)
def app(session):
    session.cd("twitch_py")
    session.run("python", "main.py")
