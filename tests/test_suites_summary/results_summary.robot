*** Settings ***
Library    Process
Library    Collections
Library    String

*** Variables ***
${RESULTS_OUTPUT_XML}    results/output.xml
${SUMMARY_SCRIPT}    scripts/robot_results_summary.py

*** Test Cases ***
Print Robot Execution Summary From Results Folder
    [Tags]  summary
    ${result}=    Run Process    python    ${SUMMARY_SCRIPT}    ${RESULTS_OUTPUT_XML}    shell=False    stdout=PIPE    stderr=PIPE
    Should Be Equal As Integers    ${result.rc}    0    msg=${result.stderr}

    @{summary_lines}=    Split To Lines    ${result.stdout}
    ${total_tests_count}=    Get Summary Value    TOTAL=    @{summary_lines}
    ${pass_tests_count}=    Get Summary Value    PASSED=    @{summary_lines}
    ${fail_tests_count}=    Get Summary Value    FAILED=    @{summary_lines}

    Log To Console    \nTotal Tests---->${total_tests_count}
    Log To Console    Passed Tests--->${pass_tests_count}
    Log To Console    Failed Tests--->${fail_tests_count}
    Log Failure Messages Section    @{summary_lines}

*** Keywords ***
Split To Lines
    [Arguments]    ${text}
    @{lines}=    Split String    ${text}    \n
    ${normalized_lines}=    Create List
    FOR    ${line}    IN    @{lines}
        ${trimmed}=    Strip String    ${line}
        IF    $trimmed != ''
            Append To List    ${normalized_lines}    ${trimmed}
        END
    END
    RETURN    @{normalized_lines}

Get Summary Value
    [Arguments]    ${prefix}    @{summary_lines}
    FOR    ${line}    IN    @{summary_lines}
        ${starts_with_prefix}=    Evaluate    $line.startswith($prefix)
        IF    ${starts_with_prefix}
            ${value}=    Replace String    ${line}    ${prefix}    ${EMPTY}
            RETURN    ${value}
        END
    END
    Fail    Could not find summary line with prefix: ${prefix}

Log Failure Messages Section
    [Arguments]    @{summary_lines}
    ${capture}=    Set Variable    ${False}
    ${current_test_name}=    Set Variable    ${EMPTY}
    Log To Console    \nError Messages Section:
    FOR    ${line}    IN    @{summary_lines}
        IF    $line == 'ERROR_MESSAGES_START'
            ${capture}=    Set Variable    ${True}
            CONTINUE
        END
        IF    $line == 'ERROR_MESSAGES_END'
            BREAK
        END
        IF    not ${capture}
            CONTINUE
        END
        IF    $current_test_name == ''
            ${current_test_name}=    Set Variable    ${line}
            Log To Console    ${current_test_name}
        ELSE
            Log To Console    ${line}
            ${current_test_name}=    Set Variable    ${EMPTY}
        END
    END
    IF    $current_test_name != ''
        Log To Console    No failure reason captured.
    END
