*** Settings ***
Resource    ../../resources/common_keywords.resource

*** Variables ***
${CLOSE_BUTTON}    xpath=//ion-fab-button[.//ion-icon[@aria-label='home'] or normalize-space(.)='home']
${PASSWORD}    id=password
${PASSWORD_TEXTBOX}    xpath=//input[@placeholder='Password']
${ION_INPUT_1_PASSWORD}    xpath=//input[@name='ion-input-1']

*** Keywords ***
Click Close Button
    Click When Ready    ${CLOSE_BUTTON}

Enter Password
    [Arguments]    ${password}
    Wait For Element To Be Ready    ${PASSWORD}
    Input Password    ${PASSWORD}    ${password}

Enter Password Textbox
    [Arguments]    ${password}
    Input Text When Ready    ${PASSWORD_TEXTBOX}    ${password}

Enter Ion Input 1 Password
    [Arguments]    ${password}
    Wait For Element To Be Ready    ${ION_INPUT_1_PASSWORD}
    Input Password    ${ION_INPUT_1_PASSWORD}    ${password}
