#!/bin/bash
# Script to generate pot and po files outside of the normal build process
#
# To add create a new language file simply create the folder replace MyLanguageCode by the language code:
# mkdir ./plugin/locale/MyLanguageCode
# 
# Exemple: mkdir ./plugin/locale/fr
#
# Then run the script
#
# Pre-requisite:
# The following tools must be installed on your system and accessible from path
# gawk, find, xgettext, gsed, python, msguniq, msgmerge, msgattrib, msgfmt, msginit
##
# Author: Pr2 for OpenPLi Team
# Version: 1.0
#
extension=$(gawk -F "." '/'"'"'Extensions.*'"'"'/ { gsub(/'"'"'$/,"",$2); print $2 }' setup.py )
printf "Retrieve extension name: %s\n" $extension
printf "Po files update/creation from script starting.\n"
languages=($(ls ./plugin/locale | tr "\n" " "))
#
# Arguments to generate the pot and po files are not retrieved from the Makefile.
# So if parameters are changed in Makefile please report the same changes in this script.
#
cd plugin
printf "Creating file $extension.pot\n"
find -s -X .. -name "*.py" -exec xgettext --no-wrap -L Python --from-code=UTF-8 -kpgettext:1c,2 --add-comments="TRANSLATORS:" -d $extension -s -o $extension-py.pot {} \+
gsed --in-place $extension-py.pot --expression=s/CHARSET/UTF-8/
cat $extension-py.pot | msguniq --no-wrap --no-location -o $extension.pot -
OLDIFS=$IFS
IFS=" "
for lang in "${languages[@]}" ; do
	if [ -f ./locale/$lang/LC_MESSAGES/$extension.po ]; then \
		printf "Updating existing translation file for language %s\n" $lang
		msgmerge --backup=none --no-wrap --no-location -s -U ./locale/$lang/LC_MESSAGES/$extension.po $extension.pot && touch ./locale/$lang/LC_MESSAGES/$extension.po; \
		msgattrib --no-wrap --no-obsolete ./locale/$lang/LC_MESSAGES/$extension.po -o ./locale/$lang/LC_MESSAGES/$extension.po; \
		msgfmt -o ./locale/$lang/LC_MESSAGES/$extension.mo ./locale/$lang/LC_MESSAGES/$extension.po; \
	else \
		printf "New file created for %s, please add it to github before commit\n" $lang; \
		mkdir ./locale/$lang/LC_MESSAGES/; \
		msginit -l ./locale/$lang/LC_MESSAGES/$extension.po -o ./locale/$lang/LC_MESSAGES/$extension.po -i $extension.pot --no-translator; \
		msgfmt -o ./locale/$lang/LC_MESSAGES/$extension.mo ./locale/$lang/LC_MESSAGES/$extension.po; \
	fi
done
IFS=$OLDIFS
cd ..
printf "Po files update/creation from script finished!\n"


