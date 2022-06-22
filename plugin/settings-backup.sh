#!/bin/sh
# Backup files to harddisk backup dir

if [ -z "$1" ] ; then
	echo "usage: $0 [-a] /path/to/destination"
	exit 1
fi

AUTOINSTALL="no"
if [ "$1" == "-a" ] ; then
	AUTOINSTALL="yes"
	shift
fi

BACKUPDIR="$1"
if [ -z "$BACKUPDIR" ] ; then
	echo "No destination, aborted"
	exit 1
fi
if [ ! -d "$BACKUPDIR" ] ; then
	echo "$BACKUPDIR is not a directory, aborted"
	exit 1
fi

# local variables
BACKUPFILE=/usr/lib/enigma2/python/Plugins/Extensions/AutoBackup/backup.cfg
USER_BACKUPFILE=/etc/backup.cfg
USER_AUTOINSTALL=/etc/autoinstall
INSTALLED=/etc/installed
TEMP_INSTALLED=/tmp/installed
RESTORE_TEMP=/tmp/restore.cfg
MACADDR=`cat /sys/class/net/eth0/address | tr -d :`
[ -z "$MACADDR" ] && MACADDR=nomac

# prepare special files for backup
echo "Backup to $BACKUPDIR/backup/"
[ ! -d "$BACKUPDIR/backup" ] && mkdir -p "$BACKUPDIR/backup"

if [ "$2" == "1" -a -f "$BACKUPDIR/backup/PLi-AutoBackup.tar.gz" ] ; then
    echo "save previous backup to $BACKUPDIR/backup/"
    cd "$BACKUPDIR/backup/"
    now=$(date +"%Y%m%d_%H%M")
    tar -czf "$BACKUPDIR/backup/backup.$now.tar.gz" "PLi-AutoBackup$MACADDR.tar.gz" "autoinstall$MACADDR"
fi

for bckfile in $BACKUPFILE $USER_BACKUPFILE ; do
    if [ -f $bckfile ] ; then
	while read file ; do
		[ -f "$file" -o -d "$file" ] && echo $file >> $RESTORE_TEMP
	done < $bckfile
    fi
done

cp -f /etc/passwd /tmp && echo /tmp/passwd >> $RESTORE_TEMP
[ -f /etc/shadow ] && cp -f /etc/shadow /tmp && echo /tmp/shadow >> $RESTORE_TEMP

[ -f /etc/fstab ] && \
    grep -E ' cifs | nfs | swap |^UUID=|^LABEL=' /etc/fstab | sort -fd | uniq > /tmp/fstab && \
    echo /tmp/fstab >> $RESTORE_TEMP

# backup of the security file on a VU Duo 4K
if [ -d /usr/local/bp3 ]; then
	tar -czf "$BACKUPDIR/backup/vuduo4k-security-data-$MACADDR.tar.gz" /usr/local/bp3   2> /dev/null
fi

# backup crontab(s)
[ ! -L /etc/cron ] && [ -f /etc/cron/crontabs/root ] && cat /etc/cron/crontabs/root >> /tmp/rootcron
[ -f /var/spool/cron/root ] && cat /var/spool/cron/root >> /tmp/rootcron
[ -f /var/spool/cron/crontabs/root ] && cat /var/spool/cron/crontabs/root >> /tmp/rootcron

# remove duplicate lines in case multiple are found
awk '{!seen[$0]++};END{for(i in seen) if(seen[i]==1)print i}' /tmp/rootcron > /tmp/crontab
rm /tmp/rootcron
echo /tmp/crontab >> $RESTORE_TEMP

# create the backup tarball
tar -czf "$BACKUPDIR/backup/PLi-AutoBackup$MACADDR.tar.gz" --files-from=$RESTORE_TEMP 2> /dev/null
ln -f -s PLi-AutoBackup$MACADDR.tar.gz "$BACKUPDIR/backup/PLi-AutoBackup.tar.gz" || \
cp -p "$BACKUPDIR/backup/PLi-AutoBackup$MACADDR.tar.gz" "$BACKUPDIR/backup/PLi-AutoBackup.tar.gz"

# create the autoinstall file
if [ "$AUTOINSTALL" == "yes" -a -f $INSTALLED ] ; then
	echo "Generating $BACKUPDIR/backup/autoinstall$MACADDR"
	opkg list_installed | cut -d ' ' -f 1 > $TEMP_INSTALLED
	diff $INSTALLED $TEMP_INSTALLED | grep "^+" | grep -v "^+++ $TEMP_INSTALLED" | \
               sed 's/^+//' > "$BACKUPDIR/backup/autoinstall$MACADDR"
	if [ -f $USER_AUTOINSTALL ] ; then
		for plugin in `cat ${USER_AUTOINSTALL}`
		do
			pluginname=`echo $plugin | sed -e 's/_.*//' | sed -re 's/^.+\///'`
			mv "$BACKUPDIR/backup/autoinstall$MACADDR" "$BACKUPDIR/backup/au.$$"
			grep -v "$pluginname$" "$BACKUPDIR/backup/au.$$" > "$BACKUPDIR/backup/autoinstall$MACADDR"
		done
		cat $USER_AUTOINSTALL >> "$BACKUPDIR/backup/autoinstall$MACADDR"
	fi
	ln -f -s autoinstall$MACADDR "$BACKUPDIR/backup/autoinstall" || \
	cp -p "$BACKUPDIR/backup/autoinstall$MACADDR" "$BACKUPDIR/backup/autoinstall"
fi

# mark the backup done
touch "$BACKUPDIR/backup/.timestamp"

# cleanuo
rm -f /tmp/restore.cfg
rm -f /tmp/crontab
rm -f /tmp/fstab
rm -f /tmp/passwd
rm -f /tmp/shadow
rm -f $TEMP_INSTALLED
rm -f "$BACKUPDIR/backup/au.$$"

exit 0
