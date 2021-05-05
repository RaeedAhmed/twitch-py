#!/bin/bash
TEMPDIR=twitch-tmp
CONFDIR=$HOME/.config/twitch-py
EXEC=/usr/local/bin/twitch-py
NAME=twitch-py
BIN=https://github.com/RaeedAhmed/$NAME/releases/latest/download/$NAME
REPO=https://github.com/RaeedAhmed/$NAME.git
BACKUP=/var/local/$NAME

setup() {
    for p in curl unzip streamlink
        do
            type $p >/dev/null 2>&1 || 
            { echo >&2 "$p is not installed. Aborting."; exit 1; }
        done
    echo " > Starting twitch-py installation..."
    mkdir $TEMPDIR
    cd $TEMPDIR
    if ! [ -d $BACKUP ]; then
        sudo mkdir -p $BACKUP
        sudo touch $BACKUP/data.db
    fi
}

backupDB() {
    if [ -f $CONFDIR/data.db ]; then
        echo " > Backing up database to $BACKUP"
        sudo mv $BACKUP/data.db $BACKUP/data.db.old
        sudo mv $CONFDIR/data.db $BACKUP
    fi
}

rmFiles() {
    if [ -d "$CONFDIR" ]; then
        echo " > Removing config files"
        rm -r $CONFDIR
    else
        echo " > No config files found"
    fi
    if [ -f "$EXEC" ]; then
        echo " > Removing past exec"
        sudo rm $EXEC
    else
        echo " > No past exec"
    fi   
}

dlFiles() {
    echo " > Downloading executable"
    sudo curl -sL $BIN | sudo tee $EXEC >/dev/null
    sudo chmod +x $EXEC
    echo " > Downloading repository"
    curl -sL https://github.com/RaeedAhmed/$NAME/archive/refs/heads/master.zip -o $NAME.zip
    unzip -q $NAME.zip -d $NAME
    echo " > Configuring static files"
    mkdir $CONFDIR
    cp -R $NAME/$NAME-master/src/config $CONFDIR
    cp -R $NAME/$NAME-master/src/views $CONFDIR
    echo " > Installing Streamlink"
}

restoreDB() {
    if [ -f $BACKUP/data.db.old ]; then
    	echo " > Restoring backup DB from $BACKUP"
        cp $BACKUP/data.db $CONFDIR
    fi
}

clean_() {
    cd ..
    sudo rm -r $TEMPDIR
    echo " > Installation complete"
}

install_() {
    setup
    backupDB
    rmFiles
    dlFiles
    restoreDB
    clean_
}

uninstall_() {
    rmFiles
    if [ -d $BACKUP ]; then
        sudo rm -r $BACKUP
    else
        echo " > No backup database found"
    fi
}

while getopts iu option
do
    case "${option}"
    in
    i) install_; exit 1
    ;;
    u) uninstall_; exit 1
    ;;
    esac
done
