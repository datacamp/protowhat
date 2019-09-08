def get_ord(num):
    assert num > 0, "use strictly positive numbers in get_ord()"
    nums = {
        1: "first",
        2: "second",
        3: "third",
        4: "fourth",
        5: "fifth",
        6: "sixth",
        7: "seventh",
        8: "eight",
        9: "ninth",
        10: "tenth",
    }
    if num in nums:
        return nums[num]
    else:
        return (
            {1: "{}st", 2: "{}nd", 3: "{}rd"}.get(
                num if (num < 20) else (num % 10), "{}th"
            )
        ).format(num)


def get_times(num):
    nums = {1: "once", 2: "twice"}
    if num in nums:
        return nums[num]
    else:
        return "%s times" % get_num(num)


def get_num(num):
    nums = {
        0: "no",
        1: "one",
        2: "two",
        3: "three",
        4: "four",
        5: "five",
        6: "six",
        7: "seven",
        8: "eight",
    }
    if num in nums:
        return nums[num]
    else:
        return str(num)
