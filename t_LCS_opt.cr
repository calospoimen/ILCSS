def longest_common_substrings(s1 : String, s2 : String) : Array(String)
  n = s1.size
  m = s2.size

  prev = Array(Int32).new(m + 1, 0)   # dimensionato su s2
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

def abort_msg(msg : String)
  STDERR.puts msg
  exit(1)
end

if ARGV.size != 2
  abort_msg("use: #{PROGRAM_NAME} <string1> <string2>")
end

string1, string2 = ARGV
longest_common_substrings(string1, string2).each { |s| puts s }
exit(0)
