#!/bin/bash
CONFDIR=$HOME/.config/twitch-py
EXEC=/usr/local/bin/twitch-py
NAME=twitch-py
BIN=https://github.com/RaeedAhmed/$NAME/releases/latest/download/$NAME
REPO=https://github.com/RaeedAhmed/$NAME.git

git clone $REPO
cd $NAME

rmConf() {
if [ -d "$CONFDIR" ]; then
    echo "Removing config files..."
    rm -r $CONFDIR
else
    echo "No config files found..."
fi
}

rmExec() {
if [ -f "$EXEC" ]; then
    echo "Removing past installation..."
    sudo rm $EXEC
else
    echo "No past installation..."
fi
}

setupConf() {
rmConf
echo "Setting up static files..."
mkdir $CONFDIR
cp -R twitch_py/config $CONFDIR
cp -R twitch_py/views $CONFDIR
}

uninstall() {
rmConf
rmExec
}

dlBin() {
echo "Downloading binary"
sudo wget -q --show-progress -O $EXEC $BIN || sudo curl -sL $BIN | sudo tee $EXEC >/dev/null
sudo chmod +x $EXEC
}

rmRepo() {
    cd ..
    sudo rm -r $NAME
}

while getopts cpu option
do
    case "${option}"
    in
    u) uninstall; rmRepo; exit 1
    ;;
    esac
done

# No flags
setupConf
rmExec
dlBin
pip3 install --user --upgrade streamlink
rmRepo



