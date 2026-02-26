# Smart Questions Design Guide

## Question Design Philosophy

Your 20 questions are not just for gathering information — they are a **performance**. Each question
should demonstrate that you've analyzed the data deeply and noticed things the user didn't expect.

Always ask questions in the **user's language**.

## Question Templates

Below are template patterns in English. Adapt them using actual data points from Step 1,
and translate into the user's language at runtime.

### Category 1: Life Context (3-4 questions)

**Template**: "I noticed you have [N] transactions at [specific merchant], totaling [amount]. Are you currently [inferred situation], or [alternative]?"

Examples:
- "Your records show a high volume of food delivery orders (~[N] per month), but almost none on weekends. Is it because you're too busy to cook on workdays, or do you simply enjoy the convenience?"
- "I see a consistent spending trail near [city area]. Do you live in this neighborhood?"

### Category 2: Anomaly Exploration (3-4 questions)

**Template**: "Around [date/period], there was an unusual spending spike of [details]. Was this a [guess A], or [guess B]?"

Examples:
- "Your spending surged by [X]% in [month]. Did something special happen (moving / travel / big purchase)?"
- "You made purchases at [merchant] for [N] consecutive days — were you going through a particular phase?"

### Category 3: Financial Goals (2-3 questions)

**Template**: "Based on your spending structure, your average monthly surplus is around [amount]. Are you satisfied with that? Do you have any specific financial goals?"

Examples:
- "Your spending profile suggests you're a [type] consumer. If you received an unexpected windfall (say 100K), how would you allocate it?"
- "Are you currently investing (stocks / funds / fixed-income products)? What's your risk appetite?"

### Category 4: Spending Philosophy (2-3 questions)

**Template**: "You spend significantly more on [category A] than [category B] — is this a conscious choice or an unconscious habit?"

Examples:
- "Dining accounts for [X]% of your total spending — do you consider good food a core part of quality of life, or is this something you'd like to optimize?"
- "Your subscriptions ([list]) add up to [amount]/month — are you still actively using all of them?"

### Category 5: Hidden Patterns (3-4 questions)

**Template**: "I found an interesting pattern: [pattern description]. Is this because [hypothesis]?"

Examples:
- "Your Wednesday spending is [X]% higher than Monday — is Wednesday your 'treat day' or team dinner day?"
- "Your late-night spending is concentrated around [time range] — are these planned purchases or midnight impulse buys?"
- "Around the [date] of each month there's a fixed transfer — is this rent/mortgage or something else?"

### Category 6: Future & Aspirations (2-3 questions)

**Template**: "Based on your trends over the past [N] months, [prediction]. Do you want this trend to continue?"

Examples:
- "If I helped you build an optimization plan, which area would you most want to save on: dining, shopping, or something else?"
- "Any big plans in the next 6 months that would affect your finances (travel / job change / moving / wedding, etc.)?"
- "Do you feel your current spending level matches your income? What's your ideal savings rate?"

## Presentation Format

Present questions in a single numbered list, grouped by theme but without showing category headers
(it should feel natural, not like a questionnaire):

```
To better analyze your finances, I'd like to ask you a few questions.
Feel free to skip any you'd prefer not to answer :)

1. [Question with specific data reference]
2. [Question]
3. [Question]
...
20. [Question]
```

## Rules

1. **ALWAYS reference specific numbers** — never ask generic questions
2. **Show your work** — embed data points in the question itself
3. **Be respectful of privacy** — frame sensitive questions delicately
4. **Offer escape hatches** — let users skip questions
5. **Mix fun with serious** — not all questions should be about money
6. **End with a light question** — leave them smiling
7. **Match the user's language** — if the user writes in Chinese, ask in Chinese; if in English, ask in English
