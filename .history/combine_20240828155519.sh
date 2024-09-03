#!/bin/bash

output_file="AI_Response_Weaver_Project_Files.md"

echo "# AI Response Weaver Project Files" > $output_file

function process_file {
    local file=$1
    local filename=$(basename "$file")
    local extension="${filename##*.}"
    
    echo -e "\n## $filename" >> $output_file
    echo '```'$extension >> $output_file
    cat "$file" >> $output_file
    echo -e "\n\`\`\`" >> $output_file
}

# Process root files
for file in .gitignore README.md requirements-dev.txt requirements.txt setup.py; do
    if [[ -f $file ]]; then
        process_file $file
    fi
done

# Process ai_response_weaver directory
for file in ai_response_weaver/*.py; do
    if [[ -f $file ]]; then
        process_file $file
    fi
done

# Process config directory
if [[ -f config/config.json ]]; then
    process_file config/config.json
fi

echo "Combined project files into $output_file"