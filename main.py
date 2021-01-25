from argparse import ArgumentParser
import pandas as pd
from scipy import optimize
# pylint: disable=invalid-name


FATHER_AGE_FOR_BIRTH = (15, 70)  # Minimum and maximum age when a father can have a child
MOTHER_AGE_FOR_BIRTH = (15, 50)  # Minimum and maximum age when a mother can have a child

# Max average age for 5 continuous male generations. This means that 5 continous male
# generations cannot be more than 60x5 (300) years apart, even if few of them are each up
# to 70 years apart.
MAX_AVERAGE_AGE_FOR_05_MALE_GENERATIONS = 60
MAX_AVERAGE_AGE_FOR_10_MALE_GENERATIONS = 45
MAX_AVERAGE_AGE_FOR_05_FEMALE_GENERATIONS = 40
MAX_AVERAGE_AGE_FOR_10_FEMALE_GENERATIONS = 35

# Whether average_age constraints should be added or not.
# Only implemented for male-only and female-only lines. Constraints for mixed lines not implemented yet.
# This is not useful for estimating birthdates, but can be used to verify/disprove relationships.
ADD_AVERAGE_AGE_CONSTRAINTS = False

# What quantile from the latest possible date should be used to estimate the birth date.
# For example, 0.4 means use 40% quantile. For a person with possible range 1900-2000,
# the estimated date would be 1960 = 2000 - (2000-1900) * 0.4
QUANTILE_FROM_LATEST = 0.4


def main():
    args = parse_args()
    with open(args.path, 'r') as f:
        text = f.readlines()

    lines = [(number, line.strip()) for number, line in enumerate(text) if line.strip() and not line.startswith('#')]
    print('lines', len(lines))
    # Parse variables and their genders
    genders, rem_lines = parse_variables(lines)

    if args.target not in genders:
        raise ValueError('Target {} not defined'.format(args.target))

    c = pd.Series(0, index=list(genders.keys()))
    c.sort_index(inplace=True)

    # Parse parental relationships
    fathers, mothers, rem_lines = parse_relationships(genders, rem_lines)

    A_ub, b_ub = make_relationship_constraints(c, fathers, mothers)
    if ADD_AVERAGE_AGE_CONSTRAINTS:
        A_ub, b_ub = make_average_constraints(c, fathers, mothers, A_ub, b_ub)

    # Parse equalities and inequalities
    A_ub, b_ub, A_eq, b_eq = parse_inequalities(rem_lines, c, A_ub, b_ub)
    print('genders', len(genders))
    print('relationships', len(fathers) + len(mothers))

    solve(c, A_ub, b_ub, A_eq, b_eq, args.target, args.maxiter)


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--data-file', '-d', dest='path', required=True,
                        help='path to the file containing genealogy data')
    parser.add_argument('--target', '-t', required=True,
                        help='Target individual whose birth date is to be estimated')
    parser.add_argument('--maxiter', '-i', type=int, default=1000,
                        help='Max iterations for the linear programming algorithm (default 1000)')
    return parser.parse_args()


def parse_variables(lines):
    variables = {}
    rem_lines = []
    for i, line in lines:
        line = line.split('#', 2)[0].strip()
        if line.startswith('male ') or line.startswith('female '):
            try:
                gender, name = line.split(' ')
            except ValueError:
                print('Error in line ', i)
                raise
            variables[name] = gender
        else:
            rem_lines.append((i, line))
    return variables, rem_lines


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
                raise Exception('Line {}: Father declared multiple times'.format(i))
            fathers[child] = parent
        else:
            if child in mothers:
                raise Exception('Line {}: Mother declared multiple times'.format(i))
            mothers[child] = parent
    return fathers, mothers, rem_lines


# For example, child = 600 and male parent (530 - 585). Then:
# parent - child <= -15
# child - parent <= 70
# For female parent,
# parent - child <= -15
# child - parent <= 50
def make_relationship_constraints(c, fathers, mothers):
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


def make_average_constraints(c, fathers, mothers, A_ub, b_ub):
    i = len(b_ub) - 1  # index for A_ub and b_ub

    # Add male constraints
    for child in c.index:
        # Find 5th male ancestor for child
        j = 0
        n_th_father = child
        while True:
            j += 1
            n_th_father = fathers.get(n_th_father)
            if n_th_father is None:
                break
            if j >= 10:
                i += 1
                A_ub.loc[i] = 0
                A_ub[child].loc[i] = 1
                A_ub[n_th_father].loc[i] = -1
                b_ub.append(MAX_AVERAGE_AGE_FOR_10_MALE_GENERATIONS * j)
            elif j >= 5:
                i += 1
                A_ub.loc[i] = 0
                A_ub[child].loc[i] = 1
                A_ub[n_th_father].loc[i] = -1
                upper_limit = min(MAX_AVERAGE_AGE_FOR_05_MALE_GENERATIONS * j,
                                  MAX_AVERAGE_AGE_FOR_10_MALE_GENERATIONS * 10)
                b_ub.append(upper_limit)

    # Add female constraints
    for child in c.index:
        # Find 5th male ancestor for child
        j = 0
        n_th_mother = child
        while True:
            j += 1
            n_th_mother = mothers.get(n_th_mother)
            if n_th_mother is None:
                break
            if j >= 10:
                i += 1
                A_ub.loc[i] = 0
                A_ub[child].loc[i] = 1
                A_ub[n_th_mother].loc[i] = -1
                b_ub.append(MAX_AVERAGE_AGE_FOR_10_FEMALE_GENERATIONS * j)
            elif j >= 5:
                i += 1
                A_ub.loc[i] = 0
                A_ub[child].loc[i] = 1
                A_ub[n_th_mother].loc[i] = -1
                upper_limit = min(MAX_AVERAGE_AGE_FOR_05_FEMALE_GENERATIONS * j,
                                  MAX_AVERAGE_AGE_FOR_10_FEMALE_GENERATIONS * 10)
                b_ub.append(upper_limit)
    return A_ub, b_ub


def parse_inequalities(lines, c, A_ub, b_ub):  # pylint: disable=too-many-branches
    A_eq = pd.DataFrame(columns=c.index)
    b_eq = []
    j = -1  # index for A_eq and b_eq
    i = len(b_ub) - 1  # index for A_ub and b_ub

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


def solve(c, A_ub, b_ub, A_eq, b_eq, target, maxiter=1000):
    bounds = (-2000, 2000)
    options = {"maxiter": maxiter}

    # Find earliest date of birth
    c.loc[target] = 1
    result = optimize.linprog(
        c=c,
        A_ub=A_ub,
        b_ub=b_ub,
        A_eq=A_eq,
        b_eq=b_eq,
        bounds=bounds,
        method='simplex',
        options=options
    )
    if not result.success:
        print('Could not find the earliest date.')
        if result.status == 1:
            print('Max iterations reached. Try with larger value.')
        elif result.status == 2:
            print('Problem appears to be infeasible.')
        elif result.status == 3:
            print('Problem appears to be unbounded.')
        elif result.status == 4:
            print('Numerical difficulties encountered.')
        return
    earliest = round(result.fun)

    # Find latest date of birth
    c.loc[target] = -1
    result = optimize.linprog(
        c=c,
        A_ub=A_ub,
        b_ub=b_ub,
        A_eq=A_eq,
        b_eq=b_eq,
        bounds=bounds,
        method='simplex',
        options=options
    )
    if not result.success:
        print('Could not find the latest date.')
        if result.status == 1:
            print('Max iterations reached. Try with larger value.')
        elif result.status == 2:
            print('Problem appears to be infeasible.')
        elif result.status == 3:
            print('Problem appears to be unbounded.')
        elif result.status == 4:
            print('Numerical difficulties encountered.')
        print(result)
        return
    latest = round(result.fun * -1)

    print(f'\nEstimation for {target}:')
    print('   Possible range for birth: {} - {}'.format(earliest, latest))
    if earliest != latest:
        birthdate = round(latest - (latest - earliest - 1) * QUANTILE_FROM_LATEST)
        print('   Estimated date of birth: {} ({}% quantile from latest)'.format(
            birthdate, QUANTILE_FROM_LATEST * 100))

if __name__ == "__main__":
    main()
