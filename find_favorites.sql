select profile_data.name, profile_data.age, profile.link, 
cast(sum(interest.score) as float) / count(interest.score) * sum(interest.score) as _match,
sum(interest.score) as _sum, 
count(interest.score) as _count
from profile_interest 
inner join interest on profile_interest.interest_id = interest.id 
inner join profile_data on profile_interest.profile_data_id = profile_data.id 
inner join profile on profile_data.profile_id = profile.id 
group by profile_interest.profile_data_id order by _match desc;
