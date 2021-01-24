import pandas as pd
from scipy import optimize

DATA_FILE = 'data.txt'
OBJECTIVE = 'sakhr_ibn_habib'

FATHER_AGE_FOR_BIRTH = (15, 70)  # Minimum and maximum age when a father can have a child
MOTHER_AGE_FOR_BIRTH = (15, 50)  # Minimum and maximum age when a mother can have a child


def main():
    with open(DATA_FILE, 'r') as f:
        text = f.readlines()
    
    lines = [(number, line.strip()) for number, line in enumerate(text) if line.strip() and not line.startswith('#')]
    print('lines', len(lines))
    # Parse variables and their genders
    genders, rem_lines = parse_variables(lines)

    if OBJECTIVE not in genders:
        raise ValueError('Objective {} not defined'.format(OBJECTIVE))
    c = pd.Series(0, index=list(genders.keys()))
    c.sort_index(inplace=True)
    
    # Parse parental relationships
    fathers, mothers, rem_lines = parse_relationships(genders, rem_lines)

    A_ub, b_ub = make_relationship_constraints(c, genders, fathers, mothers)

    # Parse equalities and inequalities
    A_ub, b_ub, A_eq, b_eq = parse_inequalities(genders, rem_lines, c, A_ub, b_ub)
    print('genders', len(genders))
    print('relationships', len(fathers) + len(mothers))

    solve(c, A_ub, b_ub, A_eq, b_eq)


def parse_variables(lines):
    vars = {}
    rem_lines = []
    for i, line in lines:
        line = line.split('#', 2)[0].strip()
        if line.startswith('male ') or line.startswith('female '):
            try:
                gender, name = line.split(' ')
            except ValueError:
                print('Error in line ', i)
                raise
            vars[name] = gender
        else:
            rem_lines.append((i, line))
    return vars, rem_lines


def parse_relationships(genders, lines):
    fathers = {}
    mothers = {}
    rem_lines = []
    for i, line in lines:
        if '=' in line:
            rem_lines.append((i, line))
            continue

        line = line.split('#', 2)[0].strip()
        try:
            child, parent = line.split(' ')
        except ValueError:
            print('Error in line', i, 'Correct format is "child_name parent_name".')
            raise
        if child not in genders:
            raise ValueError('Line {}: Child  {} not declared'.format(i, child))
        if parent not in genders:
            raise ValueError('Line {}: Parent {} not declared'.format(i, parent))
        if genders[parent] == 'male':
            if child in fathers:
                raise Exception('Line {}: Father declared multiple times', i)
            fathers[child] = parent
        else:
            if child in mothers:
                raise Exception('Line {}: Mother declared multiple times', i)
            mothers[child] = parent
    return fathers, mothers, rem_lines


# For example, child = 600 and male parent (530 - 585). Then:
# parent - child <= -15
# child - parent <= 70
# For female parent,
# parent - child <= -15
# child - parent <= 50
def make_relationship_constraints(c, genders, fathers, mothers):
    A_ub = pd.DataFrame(columns=c.index)
    b_ub = []
    i = -1
    for child, father in fathers.items():
        i += 1
        A_ub.loc[i] = 0
        A_ub[child].loc[i] = 1
        A_ub[father].loc[i] = -1
        b_ub.append(FATHER_AGE_FOR_BIRTH[1])
        i += 1
        A_ub.loc[i] = 0
        A_ub[child].loc[i] = -1
        A_ub[father].loc[i] = 1
        b_ub.append(FATHER_AGE_FOR_BIRTH[0] * -1)
    for child, mother in mothers.items():
        i += 1
        A_ub.loc[i] = 0
        A_ub[child].loc[i] = 1
        A_ub[mother].loc[i] = -1
        b_ub.append(MOTHER_AGE_FOR_BIRTH[1])

        i += 1
        A_ub.loc[i] = 0
        A_ub[child].loc[i] = -1
        A_ub[mother].loc[i] = 1
        b_ub.append(MOTHER_AGE_FOR_BIRTH[0] * -1)

    return A_ub, b_ub


def parse_inequalities(genders, lines, c, A_ub, b_ub):
    A_eq = pd.DataFrame(columns=c.index)
    b_eq = []
    j = -1  # index for A_eq and b_eq
    i = A_ub.index.max()  # index for A_ub and b_ub

    for l, line in lines:
        line = line.split('#')[0].strip()
        if '=' not in line:
            raise Exception('Error in line {}: No equality found.'.format(i))
        if '>=' in line:
            raise Exception('Error in line {}: >= not allowed.'.format(i))
        if '<=' in line:
            first, second = line.split('<=')
            items = [item.strip() for item in first.split(' ') if item.strip()]
            # Add a new row
            i += 1
            A_ub.loc[i] = 0
            # Add coefficients for constraint i
            for item in items:
                if not item:
                    raise Exception('Line {}: {}'.format(l, items))
                if item.startswith('-'):
                    A_ub[item[1:]].loc[i] = -1
                elif item.startswith('+'):
                    A_ub[item[1:]].loc[i] = 1
                else:
                    A_ub[item].loc[i] = 1
            b_ub.append(int(second))
        else:  # assume equality
            first, second = line.split('=')
            items = [item.strip() for item in first.split(' ') if item.strip()]
            # Add a new row
            j += 1
            A_eq.loc[j] = 0
            # Add coefficients for constraint i
            for item in items:
                if not item:
                    raise Exception('Line {}: {}'.format(l, items))
                if item.startswith('-'):
                    A_eq[item[1:]].loc[j] = -1
                elif item.startswith('+'):
                    A_eq[item[1:]].loc[j] = 1
                else:
                    A_eq[item].loc[j] = 1
            b_eq.append(int(second))

    return A_ub, b_ub, A_eq, b_eq


def solve(c, A_ub, b_ub, A_eq, b_eq):
    bounds = (-1000, 2000)

    # Find earliest date of birth
    c.loc[OBJECTIVE] = 1
    result = optimize.linprog(
        c=c,
        A_ub=A_ub,
        b_ub=b_ub,
        A_eq=A_eq,
        b_eq=b_eq,
        bounds=bounds,
        method='simplex'
    )
    if not result.success:
        print('Could not find the earliest date.')
        return
    earliest = round(result.fun)

    # Find latest date of birth
    c.loc[OBJECTIVE] = -1
    result = optimize.linprog(
        c=c,
        A_ub=A_ub,
        b_ub=b_ub,
        A_eq=A_eq,
        b_eq=b_eq,
        bounds=bounds,
        method='simplex'
    )
    if not result.success:
        print('Could not find the latest date.')
        return
    latest = round(result.fun * -1)

    print(f'\nEstimation for {OBJECTIVE}:')
    print('   Possible range for birth: {} - {}'.format(earliest, latest))
    if earliest != latest:
        birthdate = round(latest - (latest - earliest - 1) * 0.4)
        print('   Estimated date of birth: {} (40% quantile from latest)'.format(birthdate))

if __name__ == "__main__":
    main()
