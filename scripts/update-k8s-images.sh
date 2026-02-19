#!/usr/bin/env bash
# update-k8s-images.sh
# K8s マニフェスト内の Docker Hub イメージを semver 最新安定版に更新するスクリプト
#
# 使い方:
#   ./update-k8s-images.sh [オプション] <manifest_file_or_dir...>
#
# オプション:
#   -n, --dry-run     変更内容を表示するだけで実際には書き換えない
#   -b, --no-backup   バックアップ (.bak) を作成しない
#   -h, --help        このヘルプを表示
#
# 依存コマンド: curl, jq, sed, sort

set -euo pipefail

# ── カラー出力 ─────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*" >&2; }

# ── オプション解析 ─────────────────────────────────────
DRY_RUN=false
BACKUP=true

usage() {
  sed -n '2,14p' "$0" | sed 's/^# \{0,1\}//'
  exit 0
}

FILES=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    -n|--dry-run)   DRY_RUN=true ;;
    -b|--no-backup) BACKUP=false ;;
    -h|--help)      usage ;;
    -*)             error "不明なオプション: $1"; exit 1 ;;
    *)              FILES+=("$1") ;;
  esac
  shift
done

if [[ ${#FILES[@]} -eq 0 ]]; then
  error "対象ファイルまたはディレクトリを指定してください"
  usage
fi

# ── 依存チェック ────────────────────────────────────────
for cmd in curl jq; do
  if ! command -v "$cmd" &>/dev/null; then
    error "依存コマンドが見つかりません: $cmd"
    exit 1
  fi
done

# ── Docker Hub API ─────────────────────────────────────

# Docker Hub からタグ一覧を取得する（公式イメージ対応）
# 引数: <image> (例: nginx, library/nginx, bitnami/postgresql)
fetch_tags() {
  local image="$1"
  # official image の場合 library/ プレフィックスを補完
  if [[ "$image" != */* ]]; then
    image="library/$image"
  fi

  local url="https://hub.docker.com/v2/repositories/${image}/tags?page_size=100&ordering=last_updated"
  local tags=()
  local next="$url"

  while [[ -n "$next" && "$next" != "null" ]]; do
    local resp
    resp=$(curl -fsSL "$next" 2>/dev/null) || { warn "タグ取得失敗: $image"; echo ""; return; }
    mapfile -t page_tags < <(echo "$resp" | jq -r '.results[].name // empty')
    tags+=("${page_tags[@]}")
    next=$(echo "$resp" | jq -r '.next // empty')
    # 2ページ目以降は件数が十分なので止める（semver探索なので100件で通常十分）
    break
  done

  printf '%s\n' "${tags[@]}"
}

# semver としてソート可能な形式に変換（pre-release を含む場合は除外）
# 引数: タグ一覧（stdin）
filter_semver_stable() {
  grep -E '^v?[0-9]+\.[0-9]+(\.[0-9]+)?$' | sed 's/^v//'
}

# semver ソート（Major.Minor.Patch の数値順）
sort_semver() {
  sort -t. -k1,1n -k2,2n -k3,3n
}

# 最新の semver タグを返す
# 引数: <image>
latest_semver_tag() {
  local image="$1"
  fetch_tags "$image" | filter_semver_stable | sort_semver | tail -1
}

# ── マニフェストファイル処理 ───────────────────────────

# ファイル内の image: 行を抽出して <line_number>:<full_image_ref> を返す
extract_images() {
  local file="$1"
  grep -n 'image:' "$file" | sed 's/.*image:[[:space:]]*//' | \
    grep -v '^\$' | grep -v '^#' || true
}

# イメージ参照をパースする
# 返り値: registry image tag
# 例: nginx:1.21 -> "" "nginx" "1.21"
#     ghcr.io/foo/bar:latest -> "ghcr.io" "foo/bar" "latest"
parse_image_ref() {
  local ref="$1"
  local registry="" image="" tag="latest"

  # digest (@sha256:...) は対象外
  if [[ "$ref" == *@* ]]; then
    echo "SKIP"
    return
  fi

  # tag 分離
  if [[ "$ref" == *:* ]]; then
    tag="${ref##*:}"
    ref="${ref%:*}"
  fi

  # registry 判定（ドットまたはコロンを含む最初のセグメント = registry）
  local first_segment="${ref%%/*}"
  if [[ "$first_segment" == *"."* ]] || [[ "$first_segment" == *":"* ]]; then
    registry="$first_segment"
    image="${ref#*/}"
  else
    registry=""
    image="$ref"
  fi

  echo "$registry|$image|$tag"
}

# 1ファイルの処理
process_file() {
  local file="$1"
  local changed=false
  local tmp
  tmp=$(mktemp)
  cp "$file" "$tmp"

  info "処理中: ${BOLD}$file${RESET}"

  # image: 行を1行ずつ処理
  while IFS= read -r line; do
    # image: を含む行のみ対象
    if ! echo "$line" | grep -qE '^\s*-?\s*image:'; then
      continue
    fi

    # image 参照を取り出す
    local ref
    ref=$(echo "$line" | sed 's/.*image:[[:space:]]*//' | tr -d '"'"'"' ')

    local parsed
    parsed=$(parse_image_ref "$ref")

    if [[ "$parsed" == "SKIP" ]]; then
      warn "  スキップ (digest): $ref"
      continue
    fi

    local registry image current_tag
    IFS='|' read -r registry image current_tag <<< "$parsed"

    # Docker Hub 以外はスキップ
    if [[ -n "$registry" ]]; then
      warn "  スキップ (Docker Hub 以外): $ref"
      continue
    fi

    # latest タグはスキップ（semver でないため）
    if [[ "$current_tag" == "latest" ]]; then
      warn "  スキップ (latest タグ): $ref"
      continue
    fi

    # 最新 semver タグを取得
    info "  確認中: $image (現在: $current_tag)"
    local latest_tag
    latest_tag=$(latest_semver_tag "$image")

    if [[ -z "$latest_tag" ]]; then
      warn "  semver タグが見つかりません: $image"
      continue
    fi

    if [[ "$current_tag" == "$latest_tag" ]]; then
      success "  最新です: $image:$current_tag"
      continue
    fi

    echo -e "  ${YELLOW}更新${RESET}: ${image}:${current_tag} -> ${GREEN}${image}:${latest_tag}${RESET}"

    if ! "$DRY_RUN"; then
      # image 参照を sed で置換（タグ部分のみ）
      local old_ref="${image}:${current_tag}"
      local new_ref="${image}:${latest_tag}"
      sed -i "s|${old_ref}|${new_ref}|g" "$tmp"
      changed=true
    fi

  done < "$file"

  if "$changed"; then
    if "$BACKUP"; then
      cp "$file" "${file}.bak"
      info "  バックアップ: ${file}.bak"
    fi
    mv "$tmp" "$file"
    success "  更新完了: $file"
  else
    rm -f "$tmp"
    if "$DRY_RUN"; then
      info "  [dry-run] 実際の書き換えはしていません"
    fi
  fi
}

# ── エントリポイント ────────────────────────────────────

if "$DRY_RUN"; then
  echo -e "${YELLOW}${BOLD}=== DRY-RUN モード (書き換えなし) ===${RESET}"
fi

# ファイル/ディレクトリを展開
target_files=()
for path in "${FILES[@]}"; do
  if [[ -d "$path" ]]; then
    # ディレクトリの場合は .yaml / .yml を再帰検索
    while IFS= read -r f; do
      target_files+=("$f")
    done < <(find "$path" -type f \( -name '*.yaml' -o -name '*.yml' \))
  elif [[ -f "$path" ]]; then
    target_files+=("$path")
  else
    error "ファイルまたはディレクトリが見つかりません: $path"
  fi
done

if [[ ${#target_files[@]} -eq 0 ]]; then
  error "対象の YAML ファイルが見つかりませんでした"
  exit 1
fi

echo ""
for f in "${target_files[@]}"; do
  process_file "$f"
  echo ""
done

echo -e "${BOLD}完了${RESET}"