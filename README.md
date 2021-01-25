# quraysh
Quraysh is a Python program that uses [Linear Programming](https://en.wikipedia.org/wiki/Linear_programming) to verify genealogical connections and estimate birth dates for ancient ancestors.

Individuals are declared with their gender and child-parent relationships are entered in a text file (henceforth, data file). For individuals with known birth dates, you can enter them as additional constraints.

The default data file provided contains genealogical records of pre-Islamic Arabs including the tribe of Quraysh (hence the name). Use it as a template to create your own data file.

## Arab Ancestry
There are numerous genealogical records of pre-Islamic (up to the Rashidun Caliphdate) people, with hundreds of thousands of individuals mentioned in several books written in the early centuries AH (After Hijrah).

However, there is absolutely no information about their birth dates, except for those that lived closer to the beginning of Islam. Even in such cases, the birth dates are estimates rather than absolute dates, since Arabs didn't use a calendar system until the second Rashidun Caliph Umar ibn al-Khattab created one based on the lunar months used by the Arabs.

Therefore, it is extremely hard to know when a certain individual lived in the ancient Arabia. But since there are several relationships known for such individuals, we can compute the earliest possible and latest possible birth dates (years only) for those individuals.

### Example
[Qusai ibn Kilab](https://en.wikipedia.org/wiki/Qusai_ibn_Kilab) was the fifth grandfather (male line) of the Prophet Muhammad ﷺ. We can estimate his birth date by taking 35 as the average distance between two generations.
Thus, his birth is estimated to be
```
570 - 5*35 = 395
```
(570 being the approximate birth year of the Prophet).

However, that is a very crude way of measuring birth date of a person.

If we use linear programming, we can connect Qusai ibn Kilab to all his descendants and ancestors with known birth dates (there is none in ancestors, but several in descendants). Then we can add constraints such as the following:

1. A male can give birth to a child earliest at age 15 and latest at age 70.
2. A female can have a child earliest at age 15 and latest at age 50.

This will limit the possible range of birth year for Qusai ibn Kilab to be between 348 to 442.

If further relationships are added, in his children, his siblings, or even the siblings of his ancestors, this can possibly further reduce this range. But if the currently added relationships are confirmed (some can be uncertain), we can say it is impossible that he was born outside this range.

### Birth date estimation
To estimate the year birth, we can use a simple heuristic such as the median value:

```
442 - (442 - 348 + 1) / 2
= 395
```

(+1 because the range is inclusive on both sides).

However, a better estimate is to use the 40% quantile from the top. This is because a male person's average child bearing age is not a median of [15,70] (which would be 42), but somewhere in his thirties such as 35.

Using this new heuristic, the estimated birth year of Qusai ibn Kilab would be:
```
442 - (442 - 348 + 1) * 0.4
= 405 CE.
```

## Under Development
This program and the associated data file are subject to change, since it is currently under development. Suggestions for improvement are welcome.
