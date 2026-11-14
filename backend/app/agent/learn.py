"""Step 6: feedback -> proposed lesson.

Claude turns specific feedback ("we always need a mobile layout") into one imperative lesson,
shows its evidence, and checks for duplicates (similarity > DUPLICATE_SIMILARITY) and conflicts
with approved lessons or current decisions. Nothing affects future briefs until a user approves
it and picks a scope.
"""
