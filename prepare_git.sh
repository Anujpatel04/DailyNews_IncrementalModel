#!/bin/bash
# Script to prepare repository for git push

echo "Preparing repository for git..."

# Initialize git if not already done
if [ ! -d ".git" ]; then
    echo "Initializing git repository..."
    git init
fi

# Add all files
echo "Adding files to git..."
git add .

# Show status
echo ""
echo "Git status:"
git status

echo ""
echo "Ready for commit!"
echo ""
echo "Next steps:"
echo "1. Review the files with: git status"
echo "2. Commit with: git commit -m 'Initial commit: Incremental News Intelligence System'"
echo "3. Add remote: git remote add origin <your-repo-url>"
echo "4. Push: git push -u origin main"


