library(readxl)
library(farmr)
library(tidyverse)

# importing the data sets
read_excel("C:/Users/IT SUPPORT/Desktop/2025_AHS/Kisoro/Kisoro_workplan.xlsx") -> AHS_workplan_Sam
read_excel("C:/Users/IT SUPPORT/Desktop/2025_AHS/Kisoro/Kisoro.xlsx") -> SamXPhilip

#
head(AHS_workplan_Sam)
head(SamXPhilip)


# view the data
utils::View(AHS_workplan_Sam)
utils::View(SamXPhilip)

# dimension of the SamXPhilip
dim(SamXPhilip)

# create a unique identifier for each row
#
SamXPhilip %>% 
  ungroup() %>% 
  distinct(., id, .keep_all = T) %>%
  mutate(villageidentifier = paste(str_to_title(district), str_to_title(cluster), str_to_title(village), sep = "_")) %>% 
  merge(., 
        AHS_workplan_Sam %>% 
          mutate(villageidentifier = paste(str_to_title(District), str_to_title(Cluster), str_to_title(Villages), sep = "_")) %>% 
          select(villageidentifier, DAY, DATE, `Contractors Code`),
        by = "villageidentifier",
        all.x = T) %>% #filter(is.na(`Contractors Code`)) %>% #utils::View() 
  mutate(contractor_codes = str_split(`Contractors Code`, ","),
         priority = case_when(status == "Target" ~ 1, status == "Reserve" ~ 2, 
                              TRUE ~ 3)) -> merged_case_list_AHS

# dimension of merged data
dim(merged_case_list_AHS)

# checking the duplicated AHS
merged_case_list_AHS %>% 
  mutate(dupIDs = is_duplicated(id)) %>% 
  filter(dupIDs == "TRUE") %>% 
  utils::View()

# clusters that do not have contractors
merged_case_list_AHS %>% 
  filter(is.na(`Contractors Code`)) %>% 
  group_by(district, cluster) %>% 
  tally()

# villages that do not have contractors
merged_case_list_AHS %>% 
  filter(is.na(`Contractors Code`)) %>% 
  group_by(district, cluster, village) %>% 
  tally()


# option two capping the reserves to 3 and targets to 6, shall maintain the rest as not assigned
merged_case_list_AHS %>% 
  group_by(villageidentifier, DAY) %>% 
  arrange(priority, .by_group = TRUE) %>%
  mutate(target_row = ifelse(status == "Target", row_number(), NA),
         reserve_row = ifelse(status == "Reserve", cumsum(status == "Reserve"), NA),
         other_row = ifelse(is.na(status) | (!status %in% c("Target", "Reserve")), 
                            cumsum(is.na(status) | (!status %in% c("Target", "Reserve"))), 
                            NA)) %>%
  # Assign contractors based on status
  mutate(assigned_contractor = case_when(
    status == "Target" ~ str_trim(contractor_codes[[1]])[(target_row - 1) %% length(contractor_codes[[1]]) + 1],
    status == "Reserve" ~ str_trim(contractor_codes[[1]])[(reserve_row - 1) %% length(contractor_codes[[1]]) + 1],
    TRUE ~ str_trim(contractor_codes[[1]])[(other_row - 1) %% length(contractor_codes[[1]]) + 1])) %>%
  # Add a counter for reserves per contractor
  group_by(villageidentifier, DAY, assigned_contractor) %>%
  mutate(target_count_per_contractor = cumsum(status == "Target"),
         reserve_count_per_contractor = cumsum(status == "Reserve")) %>%
  # Set assigned_contractor to NA for reserves beyond 3 per contractor and for targets beyond 6
  mutate(assigned_contractor = case_when(
    status == "Target" & target_count_per_contractor > 6 ~ "Not Assigned",
    status == "Reserve" & reserve_count_per_contractor > 3 ~ "Not Assigned",
    TRUE ~ assigned_contractor
  )) %>%
  # Clean up helper columns
  ungroup() %>%
  select(-c(contractor_codes, priority, target_row, reserve_row, other_row, target_count_per_contractor, reserve_count_per_contractor, villageidentifier)) %>%
  write.csv(., file = "C:/Users/IT SUPPORT/Desktop/2025_AHS/Kisoro/Kisoro_assigned.csv", row.names = FALSE)
  

