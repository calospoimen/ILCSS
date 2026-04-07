# String similarity test based on ILCSS Iterative Longest Common SubStrings algorithm O(mn(n/3))

(@ARGV == 2) || die "uso : $0 <stringa1> <stringa2>";
my ($str1, $str2) = @ARGV;

print ilcss_sim($str1, $str2), "\n";

exit(0);

sub abort
{
	print $_[0], "\n";
	exit(1);
}

sub ilcss_sim
{
  my ($str1, $str2) = @_;
  $str1 =~ s/\s//g;
  $str2 =~ s/\s//g;

  my ($strlen1, $strlen2, $strlen_max, @blocks, $block, $block_len, $pos1, $pos2, $distance, $distance_ratio, $block_len_ratio, $penalty_ratio, $block_score);
  $strlen1 = length($str1);
  $strlen2 = length($str2);
  if ( $strlen1 > $strlen2 )
  {
  	  $strlen_max = $strlen1;
  }
  else
  {
  	  $strlen_max = $strlen2;
  }
  my $tot_blocks_score = 0;

  do
  {
    @blocks = &lcss($str1, $str2);
    $block_len_min = length($blocks[0]);
		foreach $block (@blocks)
		{
			$block_len = length($block);
			next if $block_len < 3; # considered only substrings of length 3 at least
			$pos1 = index($str1, $block);
			$str1 = substr($str1, 0, $pos1) . "{" x $block_len . substr($str1, $pos1 + $block_len);
			$pos2 = index($str2, $block);
			$str2 = substr($str2, 0, $pos2) . "}" x $block_len . substr($str2, $pos2 + $block_len);
			$distance = abs($pos2 - $pos1);
			$distance_ratio = $distance / $strlen_max;
			$block_len_ratio = $block_len / $strlen_max;
			$penalty_ratio = $distance_ratio * (1 - $block_len_ratio); # distance of blocks has less incidence with bigger blocks
			$block_score = $block_len - $block_len * $penalty_ratio;
			$tot_blocks_score += $block_score;
		}
  } while ( $block_len_min > 2 ); # considered only substrings of length 3 at least
  return $tot_blocks_score / $strlen_max;
}

sub lcss
{
  my ($str1, $str2) = @_;
	return $str1 if $str1 eq $str2;

  my $l_length = 0; # length of longest common substring
  my $len1 = length $str1; 
  my $len2 = length $str2; 
  my @char1 = (undef, split(//, $str1)); # $str1 as array of chars, indexed from 1
  my @char2 = (undef, split(//, $str2)); # $str2 as array of chars, indexed from 1
  my @lc_suffix; # "longest common suffix" table
  my @substrings; # list of common substrings of length $l_length
 
  for my $n1 ( 1 .. $len1 )
	{ 
    for my $n2 ( 1 .. $len2 )
		{ 
      if ($char1[$n1] eq $char2[$n2])
			{
        # We have found a matching character. Is this the first matching character, or a
				# continuation of previous matching characters? If the former, then the length of
				# the previous matching portion is undefined; set to zero.
        $lc_suffix[$n1-1][$n2-1] ||= 0;
				# In either case, declare the match to be one character longer than the match of
				# characters preceding this character.
        $lc_suffix[$n1][$n2] = $lc_suffix[$n1-1][$n2-1] + 1;
				# If the resulting substring is longer than our previously recorded max length ...
        if ($lc_suffix[$n1][$n2] > $l_length)
				{
					# ... we record its length as our new max length ...
          $l_length = $lc_suffix[$n1][$n2];
					# ... and clear our result list of shorter substrings.
          @substrings = ();
        }
				# If this substring is equal to our longest ...
        if ($lc_suffix[$n1][$n2] == $l_length)
				{
					# ... add it to our list of solutions.
          push @substrings, substr($str1, ($n1-$l_length), $l_length);
        }
      }
    }
  }   
 
  return @substrings; # when the iteration finds more substrings of equal length it returns them all
}