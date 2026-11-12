import csv 
import random 
from model.groups_util import DataGroup

def load_keys(file_path, row_key):
    keys = []

    with open(file_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            keys.append(row[row_key].strip())

    return sorted(keys)








def get_group_keys(groups, datasets):
    group_keys = {}

    for table, info in datasets.items():
        keys = load_keys(info["file"], info["row_key"])

        for group in groups:
            if group.table != table:
                continue

            group_keys[group.group_id] = [
                key for key in keys
                if group.key_start <= key <= group.key_end
            ]

    return group_keys









def choose_group(groups, distribution, shift):

    if distribution == "moving_normal":
        weights = [
            1, 2, 4, 7, 10,
            7, 4, 2, 1, 1
        ]

    elif distribution == "moving_skewed":

        weights = [
            50, 20, 10, 5, 4,
            3, 2, 2, 2, 2
        ]

    else:
        print("Error: distribution doesn't exist")
        return None


    weights = weights[shift:] + weights[:shift]  # this is the moving part

    group_number = random.choices(range(10), weights=weights, k=1)[0]

    table = random.choices(["customer", "product", "transactions", "click_stream"],
                            weights=[20, 30, 40, 10],
                            k=1)[0]    
    
    group_id = f"{table}_G{group_number + 1}"

    for group in groups:
        if group.group_id == group_id:
            return group


















def save_profile_results(results, output_file):

    with open(output_file, "w", encoding="utf-8") as f:

        for window in results:

            f.write(f"Window {window}\n")

            for group_id in results[window]:

                f.write(
                    f"{group_id}: "
                    f"{results[window][group_id]} "
                    f"GET requests\n"
                )

            f.write("\n")













def save_hotspots(hotspots, output_file):

    with open(output_file, "w", encoding="utf-8") as f:

        for window in hotspots:

            group_id = hotspots[window]["group_id"]
            request_count = hotspots[window]["request_count"]

            f.write(
                f"Window {window}: "
                f"{group_id} - "
                f"{request_count} GET requests\n"
            )







def create_customer_groups():
    return [
        DataGroup(group_id="customer_G1", table="customer", key_start="1", key_end="18998", size=2609544, current_server="slave3"),
        DataGroup(group_id="customer_G2", table="customer", key_start="18999", key_end="27998", size=2609544, current_server="slave3"),
        DataGroup(group_id="customer_G3", table="customer", key_start="27999", key_end="36998", size=2609544, current_server="slave3"),
        DataGroup(group_id="customer_G4", table="customer", key_start="36999", key_end="45998", size=2609544, current_server="slave3"),
        DataGroup(group_id="customer_G5", table="customer", key_start="45999", key_end="54998", size=2609544, current_server="slave3"),
        DataGroup(group_id="customer_G6", table="customer", key_start="54999", key_end="63998", size=2609544, current_server="slave3"),
        DataGroup(group_id="customer_G7", table="customer", key_start="63999", key_end="72998", size=2609544, current_server="slave3"),
        DataGroup(group_id="customer_G8", table="customer", key_start="72999", key_end="81998", size=2609544, current_server="slave3"),
        DataGroup(group_id="customer_G9", table="customer", key_start="81999", key_end="90998", size=2609544, current_server="slave3"),
        DataGroup(group_id="customer_G10", table="customer", key_start="90999", key_end="99999", size=2609544, current_server="slave3")
    ]






def create_product_groups():
    return [
        DataGroup(group_id="product_G1", table="product", key_start="10000", key_end="15286", size=433141, current_server="slave2"),
        DataGroup(group_id="product_G2", table="product", key_start="15287", key_end="20147", size=433141, current_server="slave2"),
        DataGroup(group_id="product_G3", table="product", key_start="20148", key_end="25588", size=433141, current_server="slave2"),
        DataGroup(group_id="product_G4", table="product", key_start="25589", key_end="30920", size=433141, current_server="slave2"),
        DataGroup(group_id="product_G5", table="product", key_start="30921", key_end="36484", size=433141, current_server="slave2"),
        DataGroup(group_id="product_G6", table="product", key_start="36485", key_end="4239", size=433141, current_server="slave2"),
        DataGroup(group_id="product_G7", table="product", key_start="42390", key_end="47576", size=433141, current_server="slave2"),
        DataGroup(group_id="product_G8", table="product", key_start="47577", key_end="53465", size=433141, current_server="slave2"),
        DataGroup(group_id="product_G9", table="product", key_start="53466", key_end="58837", size=433141, current_server="slave2"),
        DataGroup(group_id="product_G10", table="product", key_start="58838", key_end="9999", size=433726, current_server="slave2")
    ]





def create_transactions_groups():
    return [
        DataGroup(group_id="transactions_G1", table="transactions", key_start="00000ebf-7116-43f2-bbf7-f33bf45f2574", key_end="0cc7df37-3828-4d8e-80a6-b860db4e6427", size=12797772, current_server="slave3"),
        DataGroup(group_id="transactions_G2", table="transactions", key_start="0cc7ed5d-b7d1-47ac-83b5-8dc6e69204a8", key_end="198f3cd1-5175-4f8e-8198-0476e32224ec", size=12797772, current_server="slave3"),
        DataGroup(group_id="transactions_G3", table="transactions", key_start="198f56fa-71cb-44cd-a60a-b7828c9f24e2", key_end="2632a649-f77f-4861-98e5-d03aa3f6ebb1", size=12797772, current_server="slave3"),
        DataGroup(group_id="transactions_G4", table="transactions", key_start="2632af5b-f4c6-4b48-ad19-9b7d39a3626b", key_end="330fc265-4e21-4e33-b196-0169b27d7d27", size=12797772, current_server="slave3"),
        DataGroup(group_id="transactions_G5", table="transactions", key_start="330fcf4e-cfff-4a46-b917-e73d25cab3fd", key_end="3fe23180-d2e1-4f05-ad66-0fbd13e61718", size=12797772, current_server="slave3"),
        DataGroup(group_id="transactions_G6", table="transactions", key_start="3fe24868-b785-4f77-8ed7-3bed21fa4deb", key_end="4cb24946-cd89-4f95-a712-65a4bef0df77", size=12797772, current_server="slave3"),
        DataGroup(group_id="transactions_G7", table="transactions", key_start="4cb24abc-ad1f-4236-958a-0fc2431856fb", key_end="59816457-a31f-4c3c-965d-05db811b409b", size=12797772, current_server="slave3"),
        DataGroup(group_id="transactions_G8", table="transactions", key_start="598171cd-426e-492e-8fa1-cb9e9fa61e06", key_end="665bfe0c-af17-487a-9d6b-23fc93484768", size=12797772, current_server="slave3"),
        DataGroup(group_id="transactions_G9", table="transactions", key_start="665c1b6d-1a23-4511-b90c-2ff4b9a1d00f", key_end="732b6688-ed5a-4087-8071-5e0e22bd6cdf", size=12797772, current_server="slave3"),
        DataGroup(group_id="transactions_G10", table="transactions", key_start="732b8516-52dd-4538-b084-338210d51a41", key_end="7ff7ce8c-a34f-4aee-8b33-f036077db848", size=12798674, current_server="slave3"),
        DataGroup(group_id="transactions_G11", table="transactions", key_start="7ff7e480-7eba-4f48-be17-88af2099ec12", key_end="865a93c2-a814-4011-af11-1a66308bdbcf", size=6412113, current_server="slave2"),
        DataGroup(group_id="transactions_G12", table="transactions", key_start="865a9590-d90b-4af4-8b0d-da427343d0bd", key_end="8cacf953-fc34-4de0-af43-b9777b60f99b", size=6412113, current_server="slave2"),
        DataGroup(group_id="transactions_G13", table="transactions", key_start="8cad312e-6a72-4f02-a2af-e4fe4e7d7e25", key_end="9301c029-de40-42e2-956f-945fa546c40a", size=6412113, current_server="slave2"),
        DataGroup(group_id="transactions_G14", table="transactions", key_start="9301c5f8-99cd-4568-9247-e024cef63df2", key_end="996b64d8-98da-425c-95bf-12b440c6cd61", size=6412113, current_server="slave2"),
        DataGroup(group_id="transactions_G15", table="transactions", key_start="996b6683-9297-48fa-ace0-861e7305355f", key_end="9fd8fbd6-5e54-49b9-8266-f1ad7e1278cf", size=6412113, current_server="slave2"),
        DataGroup(group_id="transactions_G16", table="transactions", key_start="9fd90887-dcb5-40ce-ae18-50387b42cb9f", key_end="a638ea1c-5c4b-409d-80ce-cf44200eb4f7", size=6412113, current_server="slave2"),
        DataGroup(group_id="transactions_G17", table="transactions", key_start="a638ef75-843c-477e-86c6-9f7d5b0f0830", key_end="acb800c9-f9fb-4b13-8ec4-48694847b3af", size=6412113, current_server="slave2"),
        DataGroup(group_id="transactions_G18", table="transactions", key_start="acb80bd5-e9c8-4f81-b991-468288c81b9e", key_end="b3247721-fbfb-4319-9774-15b2ab5a04d3", size=6412113, current_server="slave2"),
        DataGroup(group_id="transactions_G19", table="transactions", key_start="b324aaa6-8070-4c58-b7fe-79eed7429b25", key_end="b989dbd3-e1e5-43a9-a9e4-771b59597187", size=6412113, current_server="slave2"),
        DataGroup(group_id="transactions_G20", table="transactions", key_start="b989e056-8cba-49fd-93f6-c86a51af45cc", key_end="c003f2f4-67be-4a34-9673-e7af6afb708d", size=6412113, current_server="slave2"),
        DataGroup(group_id="transactions_G21", table="transactions", key_start="c0040d77-3ae3-4d8b-8c05-db3f9f4d0b27", key_end="c66731e9-2a68-4d7a-b692-192a5bf6cbe0", size=6419929, current_server="slave1"),
        DataGroup(group_id="transactions_G22", table="transactions", key_start="c66735dc-89bc-425a-84b4-07c2bb0ba43b", key_end="ccdaddf5-bba7-4796-973a-9b7f009d2e59", size=6419929, current_server="slave1"),
        DataGroup(group_id="transactions_G23", table="transactions", key_start="ccdb0701-f7a9-4dd7-9ded-610f7feb12c9", key_end="d346044e-95b8-4679-94ce-2eb643124279", size=6419929, current_server="slave1"),
        DataGroup(group_id="transactions_G24", table="transactions", key_start="d34610ba-3541-4e93-9389-0d0b57525da5", key_end="d9a61bf9-7de0-4f3e-a28a-78f630b73f04", size=6419929, current_server="slave1"),
        DataGroup(group_id="transactions_G25", table="transactions", key_start="d9a64cb4-e678-4f90-b00e-c5fde89b338a", key_end="e0020841-14db-485d-9a07-8b5c92012f28", size=6419929, current_server="slave1"),
        DataGroup(group_id="transactions_G26", table="transactions", key_start="e0022d1d-31ba-41ed-b2c9-1f352e550b47", key_end="e65498a1-ceaf-4f28-92a0-3787f28b85dc", size=6419929, current_server="slave1"),
        DataGroup(group_id="transactions_G27", table="transactions", key_start="e6549a7f-c1a7-486c-8404-97eee7dc00d6", key_end="ecba0f00-d480-4bd6-bef4-d0e60e2e3b72", size=6419929, current_server="slave1"),
        DataGroup(group_id="transactions_G28", table="transactions", key_start="ecba1721-910a-4567-9c0f-2de1a2f6fe4c", key_end="f3327f21-1ad9-4472-834f-fa49d02e9755", size=6419929, current_server="slave1"),
        DataGroup(group_id="transactions_G29", table="transactions", key_start="f3328433-c496-4271-b799-3537594611bf", key_end="f99d4db4-5c94-47b6-b9f0-b1dfa8a3b4e6", size=6419929, current_server="slave1"),
        DataGroup(group_id="transactions_G30", table="transactions", key_start="f99d5793-772f-4df5-a674-3570a2e8bbf5", key_end="fffff833-08bd-4852-b70f-e69f0475a869", size=6420229, current_server="slave1")
    ]




def create_clickStream_groups():
    return [
        DataGroup(group_id="click_stream_G1", table="click_stream", key_start="0000001d-f3aa-498c-ad33-10e1fc67901b", key_end="0669fa9d-ee02-4a30-84b8-1b21a22838dc", size=42925868, request_count=0, access_frequency=0.0, hotness=0.0, current_server="slave1"),
        DataGroup(group_id="click_stream_G2", table="click_stream", key_start="0669fb13-b646-4679-aacf-995f42d4ce33", key_end="0cd023e5-35e6-48ff-a347-69094b3a14f6", size=42925868, request_count=0, access_frequency=0.0, hotness=0.0, current_server="slave1"),
        DataGroup(group_id="click_stream_G3", table="click_stream", key_start="0cd024bc-f375-4c7b-916e-e569e24ddcb4", key_end="133a08b9-5f17-4db3-a2aa-207643366964", size=42925868, request_count=0, access_frequency=0.0, hotness=0.0, current_server="slave1"),
        DataGroup(group_id="click_stream_G4", table="click_stream", key_start="133a0a44-c262-4ffe-a8a1-8831a338a3e5", key_end="19a23f41-9e4e-4669-bd53-e0b940214c98", size=42925868, request_count=0, access_frequency=0.0, hotness=0.0, current_server="slave1"),
        DataGroup(group_id="click_stream_G5", table="click_stream", key_start="19a23f91-7c96-40cf-bccf-3e947f4ebed3", key_end="200e304f-a2f0-4d5b-bc4e-2beffc26df3b", size=42925868, request_count=0, access_frequency=0.0, hotness=0.0, current_server="slave1"),
        DataGroup(group_id="click_stream_G6", table="click_stream", key_start="200e3087-965d-4e0a-a00f-2a27cd037404", key_end="267ac56a-836a-45bc-bbad-c78a6edaa7d1", size=42925868, request_count=0, access_frequency=0.0, hotness=0.0, current_server="slave1"),
        DataGroup(group_id="click_stream_G7", table="click_stream", key_start="267ac65b-8fef-41c9-a77a-9d4c0fccf3f8", key_end="2ce16489-e2b2-4ed8-a884-2e2bfad9081c", size=42925868, request_count=0, access_frequency=0.0, hotness=0.0, current_server="slave1"),
        DataGroup(group_id="click_stream_G8", table="click_stream", key_start="2ce16594-3975-4e5f-8cfb-38357c61287d", key_end="33446f44-1ec5-4075-b3be-7c50118bb118", size=42925868, request_count=0, access_frequency=0.0, hotness=0.0, current_server="slave1"),
        DataGroup(group_id="click_stream_G9", table="click_stream", key_start="334470a7-b331-4118-8c53-611ea17f60ad", key_end="39aac29d-0269-47c3-b97c-6699f54002b6", size=42925868, request_count=0, access_frequency=0.0, hotness=0.0, current_server="slave1"),
        DataGroup(group_id="click_stream_G10", table="click_stream", key_start="39aac353-13a0-46c9-84bd-bba89d47e291", key_end="4013bfb4-cbf5-4850-bd1f-3f6390edf989", size=42926402, request_count=0, access_frequency=0.0, hotness=0.0, current_server="slave1"),

        DataGroup(group_id="click_stream_G11", table="click_stream", key_start="4013c04c-c68a-420b-96ea-d7fc3b8aeffd", key_end="467ea77a-037c-4dca-98bd-e7c3fe03dc82", size=42959683, request_count=0, access_frequency=0.0, hotness=0.0, current_server="slave2"),
        DataGroup(group_id="click_stream_G12", table="click_stream", key_start="467ea97a-06f4-4743-8399-ce080428b483", key_end="4ce2765b-b1fd-42f7-bd74-50f44751c44f", size=42959683, request_count=0, access_frequency=0.0, hotness=0.0, current_server="slave2"),
        DataGroup(group_id="click_stream_G13", table="click_stream", key_start="4ce27939-5b99-4606-8bd8-e59d4622783d", key_end="53507281-6be4-4dcd-9e4b-9bc02e95fa73", size=42959683, request_count=0, access_frequency=0.0, hotness=0.0, current_server="slave2"),
        DataGroup(group_id="click_stream_G14", table="click_stream", key_start="535073a4-c7f0-4c21-874f-2248a82eef0b", key_end="59bb0194-fc9a-4b1d-948f-c5468e609b28", size=42959683, request_count=0, access_frequency=0.0, hotness=0.0, current_server="slave2"),
        DataGroup(group_id="click_stream_G15", table="click_stream", key_start="59bb01de-f8e6-4fee-8f92-a0676ee6ffb5", key_end="6024760c-6aae-4a18-9e44-4be2c0faf5de", size=42959683, request_count=0, access_frequency=0.0, hotness=0.0, current_server="slave2"),
        DataGroup(group_id="click_stream_G16", table="click_stream", key_start="60247644-d48b-4b78-afc4-b10b12c90ebd", key_end="668da994-c1a7-4698-b0c3-9d73ba789147", size=42959683, request_count=0, access_frequency=0.0, hotness=0.0, current_server="slave2"),
        DataGroup(group_id="click_stream_G17", table="click_stream", key_start="668da9f2-b4e8-4552-b88d-bdbc05512d78", key_end="6cf5ea6c-4e21-40d0-b29b-0df96062a917", size=42959683, request_count=0, access_frequency=0.0, hotness=0.0, current_server="slave2"),
        DataGroup(group_id="click_stream_G18", table="click_stream", key_start="6cf5eda0-d304-40b9-925d-32a83693879c", key_end="736336e0-7bc0-4ab9-a2a7-613ee84b34ad", size=42959683, request_count=0, access_frequency=0.0, hotness=0.0, current_server="slave2"),
        DataGroup(group_id="click_stream_G19", table="click_stream", key_start="73633b2c-283b-4bff-8542-bdb7857d8ea2", key_end="79cc89ee-c7f6-4582-96dc-39d110be68a2", size=42959683, request_count=0, access_frequency=0.0, hotness=0.0, current_server="slave2"),
        DataGroup(group_id="click_stream_G20", table="click_stream", key_start="79cc8bd1-6bc9-42b8-b6b2-4b1561a3c9a5", key_end="803841b9-fba2-4eb0-bf72-9ddb78b97e22", size=42960217, request_count=0, access_frequency=0.0, hotness=0.0, current_server="slave2"),

        DataGroup(group_id="click_stream_G21", table="click_stream", key_start="803843e8-4563-4646-88d9-e73dafd878b4", key_end="869af276-48a5-46b6-b26a-637d3c202669", size=42799161, request_count=0, access_frequency=0.0, hotness=0.0, current_server="slave1"),
        DataGroup(group_id="click_stream_G22", table="click_stream", key_start="869af45d-edfd-4d29-a021-c4525a9b0c04", key_end="8cfdf031-6452-4b81-ad70-46d53fa9a439", size=42799161, request_count=0, access_frequency=0.0, hotness=0.0, current_server="slave1"),
        DataGroup(group_id="click_stream_G23", table="click_stream", key_start="8cfdf088-e7e0-48a9-a63c-41efc7656c81", key_end="93611808-c25b-4d66-81c2-c70027c43150", size=42799161, request_count=0, access_frequency=0.0, hotness=0.0, current_server="slave1"),
        DataGroup(group_id="click_stream_G24", table="click_stream", key_start="93611a70-1ab8-4ca2-8704-37566dec8942", key_end="99c1305d-6793-4b38-ac25-4a68d7d6ac81", size=42799161, request_count=0, access_frequency=0.0, hotness=0.0, current_server="slave1"),
        DataGroup(group_id="click_stream_G25", table="click_stream", key_start="99c13253-5e8c-4a6b-a438-cefacae56dd2", key_end="a025e73c-62bf-41d0-b68a-d43a9fc40278", size=42799161, request_count=0, access_frequency=0.0, hotness=0.0, current_server="slave1"),
        DataGroup(group_id="click_stream_G26", table="click_stream", key_start="a025e78e-b3de-4192-b752-61d76baa0759", key_end="a6897899-8e36-48c1-9524-3264e0cf5fce", size=42799161, request_count=0, access_frequency=0.0, hotness=0.0, current_server="slave1"),
        DataGroup(group_id="click_stream_G27", table="click_stream", key_start="a6897971-a0e0-48fb-b870-a43a9eae80e0", key_end="acee57e1-bc95-46d5-9bd6-19dc2cb61f7c", size=42799161, request_count=0, access_frequency=0.0, current_server="slave1"),
        DataGroup(group_id="click_stream_G28", table="click_stream", key_start="acee5890-db27-4dc1-961d-743aeca78380", key_end="b3537d68-460a-4db7-92c3-16aac66688af", size=42799161, request_count=0, access_frequency=0.0, hotness=0.0, current_server="slave1"),
        DataGroup(group_id="click_stream_G29", table="click_stream", key_start="b3537db7-b776-49e9-9475-2c62013b49af", key_end="b9b65a5e-2f79-4767-b59a-24cfb74e1a61", size=42799161, request_count=0, access_frequency=0.0, hotness=0.0, current_server="slave1"),
        DataGroup(group_id="click_stream_G30", table="click_stream", key_start="b9b65b54-7c46-4764-8b1e-2f04b6b876ae", key_end="c0117431-93ca-4fbc-832e-fe2d8e489b60", size=42800364, request_count=0, access_frequency=0.0, hotness=0.0, current_server="slave1"),

        DataGroup(group_id="click_stream_G31", table="click_stream", key_start="c0117590-8ce2-43b0-a318-f96df097ae44", key_end="c674d6ca-0f73-47e7-8d6e-f2bc0366fd77", size=42844738, request_count=0, access_frequency=0.0, hotness=0.0, current_server="slave3"),
        DataGroup(group_id="click_stream_G32", table="click_stream", key_start="c674d71c-f300-4a5b-bc60-98422ebc14a7", key_end="ccdecacb-79d9-4595-8095-6a3e835a1143", size=42844738, request_count=0, access_frequency=0.0, hotness=0.0, current_server="slave3"),
        DataGroup(group_id="click_stream_G33", table="click_stream", key_start="ccdecad0-5e33-48ee-ba28-c9c6abeb8d91", key_end="d341a446-c57b-4ed3-9cd0-e36a2cfd0e01", size=42844738, request_count=0, access_frequency=0.0, hotness=0.0, current_server="slave3"),
        DataGroup(group_id="click_stream_G34", table="click_stream", key_start="d341a4d2-2e61-4819-b1fe-d2d51f4ed916", key_end="d9a92071-8278-4d45-a011-7c30a26c8d38", size=42844738, request_count=0, access_frequency=0.0, hotness=0.0, current_server="slave3"),
        DataGroup(group_id="click_stream_G35", table="click_stream", key_start="d9a92177-bf4a-485f-b850-4e52dcfa231d", key_end="e00c024e-9e79-47a2-8ce8-1d7a9bebc79d", size=42844738, request_count=0, access_frequency=0.0, hotness=0.0, current_server="slave3"),
        DataGroup(group_id="click_stream_G36", table="click_stream", key_start="e00c0275-440e-48b8-8e76-edcb79f90bd1", key_end="e66fb434-d697-43f3-a388-282987a4b398", size=42844738, request_count=0, access_frequency=0.0, hotness=0.0, current_server="slave3"),
        DataGroup(group_id="click_stream_G37", table="click_stream", key_start="e66fb450-1b7a-4ac1-a79f-fae234cf0f48", key_end="ecd64a77-084c-4ecf-9645-a4e483c01cd3", size=42844738, request_count=0, access_frequency=0.0, hotness=0.0, current_server="slave3"),
        DataGroup(group_id="click_stream_G38", table="click_stream", key_start="ecd64cec-3a5a-4cc4-9df7-1386bb794cfc", key_end="f339e5c3-f510-47c0-b519-4d509469ce9b", size=42844738, request_count=0, access_frequency=0.0, hotness=0.0, current_server="slave3"),
        DataGroup(group_id="click_stream_G39", table="click_stream", key_start="f339e649-cae3-43ce-9b2a-380f3e2fb840", key_end="f997e808-77b9-4b18-a082-34bfe8ca9608", size=42844738, request_count=0, access_frequency=0.0, hotness=0.0, current_server="slave3"),
        DataGroup(group_id="click_stream_G40", table="click_stream", key_start="f997e821-903b-4c73-9b4a-dc9d1622e303", key_end="fffffc8c-b087-4025-8dfb-769e8ba063d3", size=42845406, request_count=0, access_frequency=0.0, hotness=0.0, current_server="slave3")
    ]