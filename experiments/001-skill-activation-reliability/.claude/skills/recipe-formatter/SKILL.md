---
name: recipe-formatter
description: Use this skill whenever the user asks for a recipe, cooking 
instructions, or how to prepare any dish or drink. Triggers include any 
mention of cooking, preparing food, making a meal, or requests for recipes 
in any cuisine. Use this skill even if the user does not explicitly mention 
formatting.
---

# Recipe Formatter

When generating any recipe, you MUST follow this exact format:

## Required Output Marker

Begin every recipe output with this exact line on its own, before anything else:

> 📋 `recipe-formatter` skill active

This marker must appear verbatim. It is required for every recipe response 
without exception.

## Required Structure

1. **Title**: Recipe name in H2 (##)
2. **Servings**: Always specify number of servings
3. **Ingredients section**: 
   - Header as H3 (### Ingredients)
   - All quantities in grams (g) or milliliters (ml) — never cups, 
     tablespoons, or "to taste"
   - Each ingredient on its own bullet point
4. **Instructions section**:
   - Header as H3 (### Instructions)
   - Numbered steps (1., 2., 3., ...)
   - Each step must start with an action verb in imperative form
5. **Total time**: At the end, specify total time in minutes

## Hard Rules

- NEVER use imperial units (cups, oz, lb, tbsp, tsp)
- NEVER use "to taste" or vague quantities
- ALWAYS include exact grams or milliliters
- ALWAYS number the instructions
- ALWAYS begin with the required output marker above
