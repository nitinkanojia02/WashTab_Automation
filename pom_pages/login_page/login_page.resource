*** Settings ***
Resource    ../../resources/common_keywords.resource

*** Variables ***
${LOGIN_PAGE_URL}    http://172.21.166.115/washtabui/login?data=undefined
${USER_NAME_TEXTBOX}    xpath=//input[@placeholder='User Name']
${PASSWORD_TEXTBOX}    xpath=//input[@placeholder='Password']
${SIGN_IN_BUTTON}    xpath=//ion-button[normalize-space(.)='SIGN IN']
${VALID_USERNAME}    haklarr
${VALID_PASSWORD}    Icstunnel1
${INVALID_USERNAME}    invaliduser
${INVALID_PASSWORD}    WrongPass123

*** Keywords ***
Verify Login Page Loaded
    Wait For Element To Be Ready    ${USER_NAME_TEXTBOX}
    Wait For Element To Be Ready    ${PASSWORD_TEXTBOX}
    Wait For Element To Be Ready    ${SIGN_IN_BUTTON}

Enter Username
    [Arguments]    ${text}
    Input Text When Ready    ${USER_NAME_TEXTBOX}    ${text}

Enter Password
    [Arguments]    ${text}
    Input Text When Ready    ${PASSWORD_TEXTBOX}    ${text}

Click Sign In Button
    Click When Ready    ${SIGN_IN_BUTTON}

Submit Login With Enter Key
    Press Keys    ${PASSWORD_TEXTBOX}    ENTER

Verify Login Rejected
    Wait For Element To Be Ready    ${USER_NAME_TEXTBOX}
    Wait For Element To Be Ready    ${PASSWORD_TEXTBOX}
    Wait For Element To Be Ready    ${SIGN_IN_BUTTON}

Verify Username Required Validation
    Wait For Element To Be Ready    ${USER_NAME_TEXTBOX}

Verify Password Required Validation
    Wait For Element To Be Ready    ${PASSWORD_TEXTBOX}
