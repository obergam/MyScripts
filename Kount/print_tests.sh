#!/bin/bash
# Run this script at the top level directory of a repository in which you'd like to search for tests

find . -name "*.test.ts" -print0 | while read -d $'\0' file
do
	echo '================================================================================================='
	echo '                                                                        '
	echo "                ${file}                "
	echo '                                                                        ' 
	echo '================================================================================================='
	grep "describe(\| it(" $file 
done
