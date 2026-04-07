def longest_common_substrings(s1 : String, s2 : String) : Array(String)
  n = s1.size
  m = s2.size

  prev = Array(Int32).new(m + 1, 0)
  curr = Array(Int32).new(m + 1, 0)

  best_len = 0
  results = [] of String

  (1..n).each do |i|                   # loop esterno: s1
    (1..m).each do |j|                 # loop interno: s2
      if s1[i - 1] == s2[j - 1]
        curr[j] = prev[j - 1] + 1
        if curr[j] > best_len
          best_len = curr[j]
          results = [s1[i - best_len, best_len]]
        elsif curr[j] == best_len
          results.push(s1[i - best_len, best_len])
        end
      end
    end
    prev, curr = curr, prev
    curr = Array(Int32).new(m + 1, 0)
  end

  results
end

def ilcss_sim(s1 : String, s2 : String) : Float64
  str1 = s1.gsub(/\s/, "")
  str2 = s2.gsub(/\s/, "")

  strlen_max = {str1.size, str2.size}.max.to_f
  tot_blocks_score = 0.0

  loop do
    blocks = longest_common_substrings(str1, str2)
    block_len_min = blocks.empty? ? 0 : blocks.first.size

    blocks.each do |block|
      block_len = block.size
      next if block_len < 3

      # The same block string can appear multiple times in `blocks` (duplicate
      # DP cells) but only once in one of the strings; skip rather than panic.
      pos1 = str1.index(block)
      next if pos1.nil?
      pos2 = str2.index(block)
      next if pos2.nil?

      str1 = str1[0, pos1] + "{" * block_len + str1[pos1 + block_len..]
      str2 = str2[0, pos2] + "}" * block_len + str2[pos2 + block_len..]

      distance = (pos2 - pos1).abs.to_f
      distance_ratio = distance / strlen_max
      block_len_ratio = block_len.to_f / strlen_max
      penalty_ratio = distance_ratio * (1.0 - block_len_ratio)
      block_score = block_len - block_len * penalty_ratio
      tot_blocks_score += block_score
    end

    break unless block_len_min > 2
  end

  tot_blocks_score / strlen_max
end

def abort_msg(msg : String)
  STDERR.puts msg
  exit(1)
end

if ARGV.size != 2
  abort_msg("use: #{PROGRAM_NAME} <string1> <string2>")
end

string1, string2 = ARGV
puts ilcss_sim(string1, string2)
exit(0)
