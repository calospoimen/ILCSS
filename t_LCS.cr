def longest_common_substring(s1 : String, s2 : String)
  m = Array.new(s1.size+1){ [0] * (s2.size+1) }
  longest_length, longest_end_pos = 0,0
  (1 .. s1.size).each do |x|
    (1 .. s2.size).each do |y|
      if s1[x-1] == s2[y-1]
        m[x][y] = m[x-1][y-1] + 1
        if m[x][y] > longest_length
          longest_length = m[x][y]
          longest_end_pos = x
        end
		  end
    end
  end
  return s1[longest_end_pos - longest_length ... longest_end_pos]
end

def abort_msg(msg : String)
  STDERR.puts msg
  exit(1)
end

if ARGV.size != 2
  abort_msg("use: #{PROGRAM_NAME} <string1> <string2>")
end

string1, string2 = ARGV
puts longest_common_substring(string1, string2)
exit(0)
