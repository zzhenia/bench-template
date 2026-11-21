# core/shell/lib.zsh — shared by bench.zsh, wp, cw and sync-projects.sh.
# Finds the bench root and reads this bench's settings, with no forks (it runs
# on every new terminal).
#
#   bench_shell_init <root>   sets BENCH_HOME, BENCH_CFG (assoc: config/bench.env)
#                             and BENCH_PROJECTS / BENCH_PROJECT_MODES
#                             (config/projects.tsv)
#   bench_cfg KEY [default]   env var wins, then config/bench.env, then default;
#                             a leading ~ is expanded. Sets REPLY.

bench_shell_init() {
  emulate -L zsh
  typeset -g BENCH_HOME=${BENCH_ROOT:-$1}
  typeset -gA BENCH_CFG=()
  typeset -ga BENCH_PROJECTS=() BENCH_PROJECT_MODES=()
  local line k v p m
  if [[ -r $BENCH_HOME/config/bench.env ]]; then
    while IFS= read -r line || [[ -n $line ]]; do
      [[ $line == [A-Za-z_]*=* ]] || continue
      k=${line%%=*} v=${line#*=}
      v=${v#[\"\']} v=${v%[\"\']}
      BENCH_CFG[$k]=$v
    done < "$BENCH_HOME/config/bench.env"
  fi
  # config/projects.tsv: <path> TAB <mode>. Order = menu digits. A path may
  # start with ~ or be relative to the bench root ("." is the bench itself).
  # mode: bench (picker) | claude (named session) | none — read by sync-projects.sh.
  if [[ -r $BENCH_HOME/config/projects.tsv ]]; then
    while IFS=$'\t' read -r p m || [[ -n $p ]]; do
      [[ -z $p || $p == \#* ]] && continue
      [[ $p == '~'* ]] && p=$HOME${p#\~}
      [[ $p == /* ]] || p=$BENCH_HOME/$p
      BENCH_PROJECTS+=("${p:a}")
      BENCH_PROJECT_MODES+=("${m:-claude}")
    done < "$BENCH_HOME/config/projects.tsv"
  fi
}

bench_cfg() {
  local key=$1
  REPLY=${(P)key}
  [[ -z $REPLY ]] && REPLY=${BENCH_CFG[$key]}
  [[ -z $REPLY ]] && REPLY=$2
  [[ $REPLY == '~'* ]] && REPLY=$HOME${REPLY#\~}
  return 0
}
