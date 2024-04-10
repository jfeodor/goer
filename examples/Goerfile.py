import goer

my_other_job = goer.job(
    "echo other job",
    "sleep 0.5",
    "echo other job done",
)

my_job = goer.job(
    "echo my job",
    "sleep 0.5",
    "echo my job done",
    depends_on=[my_other_job],
)

my_third_job = goer.job(
    "sleep 1",
    "echo third job",
    "sleep 1",
    "echo third job done",
)

my_root_job = goer.job(depends_on=[my_job, my_third_job])
