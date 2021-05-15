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
    mkdir $CONFDIR
    if [[ $1 = "download" ]]
    then
        mkdir $TEMPDIR
        cd $TEMPDIR
    fi
    if ! [ -d $BACKUP ]; then
        sudo mkdir -p $BACKUP
        sudo touch $BACKUP/data.db
    fi
}

backup_db() {
    if [ -f $CONFDIR/data.db ]; then
        echo " > Backing up database to $BACKUP"
        sudo mv $BACKUP/data.db $BACKUP/data.db.old
        sudo mv $CONFDIR/data.db $BACKUP
    fi
}

rm_files() {
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

dl_files() {
    echo " > Downloading repository"
    curl -sL https://github.com/RaeedAhmed/$NAME/archive/refs/heads/master.zip -o $NAME.zip
    unzip -q $NAME.zip -d $NAME
    echo " > Configuring static files"
    cp -R $NAME/$NAME-master/src/static $CONFDIR
    cp -R $NAME/$NAME-master/src/views $CONFDIR
}

dl_exec() {
    echo " > Downloading executable"
    sudo curl -sL $BIN | sudo tee $EXEC >/dev/null
    sudo chmod +x $EXEC
}

restore_db() {
    if [ -f $BACKUP/data.db.old ]; then
    	echo " > Restoring backup DB from $BACKUP"
        cp $BACKUP/data.db $CONFDIR
    fi
}

clean_() {
    cd ..
    sudo rm -r $TEMPDIR
}

download_install() {
    dl_files
    dl_exec
    clean_
}

local_install() {
    echo " > Spawning environment"
    python3 -m venv .tmpv
    source .tmpv/bin/activate
    echo " > Loading dependencies"
    pip install -q -r requirements.txt
    pip install -q pyinstaller
    echo " > Compiling binary"
    pyinstaller src/main.py --name "$NAME" --onefile --log-level=CRITICAL
    deactivate
    sudo mv dist/$NAME $EXEC
    rm -r dist build .tmpv "$NAME.spec"
    cp README.md $CONFDIR
    cp -R src/static $CONFDIR
    cp -R src/views $CONFDIR
}

installation() {
    setup $1
    backup_db
    rm_files

    if [[ $1 = "download" ]]
    then
        download_install
    else
        local_install
    fi

    restore_db
    echo " > Installation complete. Run 'twitch-py' to begin."
}

uninstall_() {
    rm_files
    if [ -d $BACKUP ]; then
        sudo rm -r $BACKUP
    else
        echo " > No backup database found"
    fi
    echo " > twitch-py uninstalled"
}

documentation() {
    echo "
Usage: install -[arg]

    -d	Download exec and files from repo
    -l	Locally compile and install program
    -u	Uninstall binary, config files, and backup db
    -h 	View this documentation
"
}

while getopts dluh option
do
    case "${option}"
    in
    d) installation "download"; exit 1
    ;;
    l) installation "local"; exit 1
    ;;
    u) uninstall_; exit 1
    ;;
    h) documentation; exit 1
    ;;
    esac
done

documentation